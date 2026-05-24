import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from app.constants import UTC

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.routes import router
from app.config import settings
from app.constants import STALE_TELEMETRY_SECONDS
from app.db.base import Base
from app.db.constraints import ensure_db_constraints
from app.db.session import AsyncSessionLocal, engine
from app.models import (  # noqa: F401 — register all tables with Base.metadata
    Anomaly,
    MaintenanceRecord,
    Mission,
    ProcessedIdempotencyKey,
    TelemetryEvent,
    VehicleCurrentState,
    ZoneCount,
)
from app.services.telemetry import (
    get_fleet_aggregate,
    get_latest_anomaly_per_vehicle,
    seed_database,
)
from app.ws.manager import ws_manager


async def stale_telemetry_checker() -> None:
    while True:
        await asyncio.sleep(5)
        cutoff = datetime.now(UTC) - timedelta(seconds=STALE_TELEMETRY_SECONDS)
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(VehicleCurrentState).where(
                    VehicleCurrentState.last_seen < cutoff
                )
            )
            stale_vehicles = result.scalars().all()
            for vehicle in stale_vehicles:
                existing = await session.execute(
                    select(Anomaly)
                    .where(
                        Anomaly.vehicle_id == vehicle.vehicle_id,
                        Anomaly.anomaly_type == "stale_telemetry",
                        Anomaly.detected_at >= cutoff,
                    )
                    .limit(1)
                )
                if existing.scalar_one_or_none():
                    continue
                session.add(
                    Anomaly(
                        vehicle_id=vehicle.vehicle_id,
                        anomaly_type="stale_telemetry",
                        message=f"No telemetry for > {STALE_TELEMETRY_SECONDS}s (last seen {vehicle.last_seen.isoformat()})",
                        detected_at=datetime.now(UTC),
                    )
                )
            if stale_vehicles:
                await session.commit()
                await ws_manager.broadcast(
                    "stale_check", {"count": len(stale_vehicles)}
                )


async def fleet_snapshot_broadcaster() -> None:
    while True:
        await asyncio.sleep(2)
        async with AsyncSessionLocal() as session:
            aggregate = await get_fleet_aggregate(session)
            vehicles = (
                (await session.execute(select(VehicleCurrentState))).scalars().all()
            )
            latest = await get_latest_anomaly_per_vehicle(session)
            from app.models import ZoneCount

            zones = (await session.execute(select(ZoneCount))).scalars().all()
            await ws_manager.broadcast(
                "fleet_snapshot",
                {
                    "aggregate": aggregate,
                    "vehicles": [
                        {
                            "vehicle_id": v.vehicle_id,
                            "status": v.status,
                            "battery_pct": v.battery_pct,
                            "speed_mps": v.speed_mps,
                            "last_seen": v.last_seen.isoformat(),
                            "last_zone": v.last_zone,
                            "latest_anomaly": (
                                {
                                    "anomaly_type": a.anomaly_type,
                                    "message": a.message,
                                    "detected_at": a.detected_at.isoformat(),
                                }
                                if (a := latest.get(v.vehicle_id))
                                else None
                            ),
                        }
                        for v in vehicles
                    ],
                    "zones": [
                        {"zone_id": z.zone_id, "entry_count": z.entry_count}
                        for z in zones
                    ],
                },
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await ensure_db_constraints(conn)
    async with AsyncSessionLocal() as session:
        await seed_database(session)

    stale_task = asyncio.create_task(stale_telemetry_checker())
    snapshot_task = asyncio.create_task(fleet_snapshot_broadcaster())
    yield
    stale_task.cancel()
    snapshot_task.cancel()


app = FastAPI(title="Fleet Telemetry Service", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws/fleet")
async def websocket_fleet(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
