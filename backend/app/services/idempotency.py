from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProcessedIdempotencyKey, TelemetryEvent, VehicleCurrentState


async def begin_idempotent_request(
    session: AsyncSession, key: str | None
) -> ProcessedIdempotencyKey | None:
    if not key:
        return None

    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
        {"key": key},
    )
    return await session.get(ProcessedIdempotencyKey, key)


async def get_telemetry_replay(
    session: AsyncSession,
    record: ProcessedIdempotencyKey,
) -> tuple[TelemetryEvent, list[str], bool, int | None]:
    event = await session.get(TelemetryEvent, record.telemetry_event_id)
    if event is None:
        raise ValueError(
            f"Stored telemetry event missing for idempotency key: {record.key}"
        )
    return (
        event,
        list(record.anomalies_detected),
        record.mission_cancelled,
        record.maintenance_record_id,
    )


async def get_status_update_replay(
    session: AsyncSession,
    record: ProcessedIdempotencyKey,
) -> tuple[VehicleCurrentState, bool, int | None]:
    result = await session.execute(
        select(VehicleCurrentState).where(
            VehicleCurrentState.vehicle_id == record.vehicle_id
        )
    )
    state = result.scalar_one_or_none()
    if state is None:
        raise ValueError(f"Stored vehicle missing for idempotency key: {record.key}")
    return state, record.mission_cancelled, record.maintenance_record_id


async def save_idempotency_record(
    session: AsyncSession, record: ProcessedIdempotencyKey
) -> None:
    session.add(record)
