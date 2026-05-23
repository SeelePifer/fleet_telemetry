from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Anomaly,
    ProcessedIdempotencyKey,
    TelemetryEvent,
    VehicleCurrentState,
)
from app.schemas import StatusUpdateIn, TelemetryIn
from app.services.idempotency import (
    begin_idempotent_request,
    get_status_update_replay,
    get_telemetry_replay,
    save_idempotency_record,
)
from app.services.telemetry import (
    detect_anomalies,
    handle_fault_transition,
    increment_zone_count,
)
from app.ws.manager import ws_manager


async def _get_vehicle_for_update(
    session: AsyncSession,
    vehicle_id: str,
) -> VehicleCurrentState | None:
    result = await session.execute(
        select(VehicleCurrentState)
        .where(VehicleCurrentState.vehicle_id == vehicle_id)
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def ingest_telemetry(
    session: AsyncSession,
    payload: TelemetryIn,
    idempotency_key: str | None = None,
) -> tuple[TelemetryEvent, list[str], bool, int | None]:
    existing_idempotency = await begin_idempotent_request(session, idempotency_key)
    if existing_idempotency is not None:
        if existing_idempotency.operation != "telemetry":
            raise ValueError("Idempotency-Key already used for a different operation")
        return await get_telemetry_replay(session, existing_idempotency)

    previous = await _get_vehicle_for_update(session, payload.vehicle_id)
    previous_status = previous.status if previous else None

    event = TelemetryEvent(
        vehicle_id=payload.vehicle_id,
        timestamp=payload.timestamp,
        lat=payload.lat,
        lon=payload.lon,
        battery_pct=payload.battery_pct,
        speed_mps=payload.speed_mps,
        status=payload.status,
        error_codes=payload.error_codes,
        zone_entered=payload.zone_entered,
    )
    session.add(event)
    await session.flush()

    if previous is None:
        previous = VehicleCurrentState(
            vehicle_id=payload.vehicle_id,
            last_seen=payload.timestamp,
            status=payload.status,
            battery_pct=payload.battery_pct,
            speed_mps=payload.speed_mps,
            lat=payload.lat,
            lon=payload.lon,
            last_zone=payload.zone_entered or None,
        )
        session.add(previous)
    else:
        previous.last_seen = payload.timestamp
        previous.status = payload.status
        previous.battery_pct = payload.battery_pct
        previous.speed_mps = payload.speed_mps
        previous.lat = payload.lat
        previous.lon = payload.lon
        if payload.zone_entered:
            previous.last_zone = payload.zone_entered
        previous.updated_at = datetime.now(UTC)

    if payload.zone_entered:
        await increment_zone_count(session, payload.zone_entered)

    anomaly_types: list[str] = []
    for anomaly_type, message in detect_anomalies(event):
        session.add(
            Anomaly(
                vehicle_id=payload.vehicle_id,
                anomaly_type=anomaly_type,
                message=message,
                detected_at=payload.timestamp,
                telemetry_event_id=event.id,
            )
        )
        anomaly_types.append(anomaly_type)

    mission_cancelled, maintenance_id = await handle_fault_transition(
        session,
        payload.vehicle_id,
        previous_status,
        payload.status,
        reason=f"Fault detected via telemetry: {', '.join(anomaly_types) or 'status=fault'}",
    )

    if idempotency_key:
        await save_idempotency_record(
            session,
            ProcessedIdempotencyKey(
                key=idempotency_key,
                operation="telemetry",
                vehicle_id=payload.vehicle_id,
                telemetry_event_id=event.id,
                anomalies_detected=anomaly_types,
                mission_cancelled=mission_cancelled,
                maintenance_record_id=maintenance_id,
            ),
        )

    await session.commit()
    await session.refresh(event)

    await ws_manager.broadcast(
        "telemetry",
        {
            "vehicle_id": payload.vehicle_id,
            "status": payload.status,
            "battery_pct": payload.battery_pct,
            "anomalies": anomaly_types,
            "zone_entered": payload.zone_entered,
        },
    )

    return event, anomaly_types, mission_cancelled, maintenance_id


async def update_vehicle_status(
    session: AsyncSession,
    vehicle_id: str,
    payload: StatusUpdateIn,
    idempotency_key: str | None = None,
) -> tuple[VehicleCurrentState, bool, int | None]:
    existing_idempotency = await begin_idempotent_request(session, idempotency_key)
    if existing_idempotency is not None:
        if existing_idempotency.operation != "status_update":
            raise ValueError("Idempotency-Key already used for a different operation")
        if existing_idempotency.vehicle_id != vehicle_id:
            raise ValueError("Idempotency-Key belongs to a different vehicle")
        return await get_status_update_replay(session, existing_idempotency)

    state = await _get_vehicle_for_update(session, vehicle_id)
    if state is None:
        raise ValueError(f"Unknown vehicle_id: {vehicle_id}")

    previous_status = state.status
    state.status = payload.status
    state.updated_at = datetime.now(UTC)

    mission_cancelled, maintenance_id = await handle_fault_transition(
        session,
        vehicle_id,
        previous_status,
        payload.status,
        reason="Manual status update to fault",
    )

    if idempotency_key:
        await save_idempotency_record(
            session,
            ProcessedIdempotencyKey(
                key=idempotency_key,
                operation="status_update",
                vehicle_id=vehicle_id,
                mission_cancelled=mission_cancelled,
                maintenance_record_id=maintenance_id,
                response_status=payload.status,
            ),
        )

    await session.commit()
    await session.refresh(state)

    await ws_manager.broadcast(
        "status_update",
        {"vehicle_id": vehicle_id, "status": payload.status},
    )

    return state, mission_cancelled, maintenance_id


async def query_anomalies(
    session: AsyncSession,
    vehicle_id: str | None,
    start: datetime | None,
    end: datetime | None,
    limit: int = 100,
) -> list[Anomaly]:
    stmt = select(Anomaly).order_by(Anomaly.detected_at.desc()).limit(limit)
    if vehicle_id:
        stmt = stmt.where(Anomaly.vehicle_id == vehicle_id)
    if start:
        stmt = stmt.where(Anomaly.detected_at >= start)
    if end:
        stmt = stmt.where(Anomaly.detected_at <= end)
    result = await session.execute(stmt)
    return list(result.scalars().all())
