from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import VehicleCurrentState, ZoneCount
from app.schemas import (
    AnomalyOut,
    FleetAggregateOut,
    StatusUpdateIn,
    StatusUpdateOut,
    TelemetryIn,
    TelemetryResponse,
    VehicleStateOut,
    ZoneCountOut,
)
from app.services.ingest import ingest_telemetry, query_anomalies, update_vehicle_status
from app.services.telemetry import get_fleet_aggregate, get_latest_anomaly_per_vehicle

router = APIRouter()


@router.post("/telemetry", response_model=TelemetryResponse)
async def post_telemetry(
    payload: TelemetryIn,
    db: AsyncSession = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    try:
        event, anomalies, _, _ = await ingest_telemetry(
            db, payload, idempotency_key=idempotency_key
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return TelemetryResponse(
        id=event.id,
        vehicle_id=event.vehicle_id,
        timestamp=event.timestamp,
        status=event.status,
        anomalies_detected=anomalies,
    )


@router.get("/zones/counts", response_model=list[ZoneCountOut])
async def get_zone_counts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ZoneCount).order_by(ZoneCount.zone_id))
    rows = result.scalars().all()
    return [
        ZoneCountOut(
            zone_id=row.zone_id, entry_count=row.entry_count, updated_at=row.updated_at
        )
        for row in rows
    ]


@router.patch("/vehicles/{vehicle_id}/status", response_model=StatusUpdateOut)
async def patch_vehicle_status(
    vehicle_id: str,
    payload: StatusUpdateIn,
    db: AsyncSession = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    try:
        state, mission_cancelled, maintenance_id = await update_vehicle_status(
            db,
            vehicle_id,
            payload,
            idempotency_key=idempotency_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return StatusUpdateOut(
        vehicle_id=state.vehicle_id,
        status=state.status,
        mission_cancelled=mission_cancelled,
        maintenance_record_id=maintenance_id,
    )


@router.get("/anomalies", response_model=list[AnomalyOut])
async def get_anomalies(
    vehicle_id: str | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    rows = await query_anomalies(db, vehicle_id, start, end, limit)
    return [
        AnomalyOut(
            id=row.id,
            vehicle_id=row.vehicle_id,
            anomaly_type=row.anomaly_type,
            message=row.message,
            detected_at=row.detected_at,
        )
        for row in rows
    ]


@router.get("/fleet/aggregate", response_model=FleetAggregateOut)
async def get_fleet_aggregate_endpoint(db: AsyncSession = Depends(get_db)):
    counts = await get_fleet_aggregate(db)
    return FleetAggregateOut(**counts)


@router.get("/vehicles", response_model=list[VehicleStateOut])
async def get_vehicles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VehicleCurrentState).order_by(VehicleCurrentState.vehicle_id)
    )
    vehicles = result.scalars().all()
    latest = await get_latest_anomaly_per_vehicle(db)
    return [
        VehicleStateOut(
            vehicle_id=v.vehicle_id,
            last_seen=v.last_seen,
            status=v.status,
            battery_pct=v.battery_pct,
            speed_mps=v.speed_mps,
            lat=v.lat,
            lon=v.lon,
            last_zone=v.last_zone,
            latest_anomaly=(
                AnomalyOut(
                    id=a.id,
                    vehicle_id=a.vehicle_id,
                    anomaly_type=a.anomaly_type,
                    message=a.message,
                    detected_at=a.detected_at,
                )
                if (a := latest.get(v.vehicle_id))
                else None
            ),
        )
        for v in vehicles
    ]
