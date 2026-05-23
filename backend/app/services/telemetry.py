from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    LOW_BATTERY_THRESHOLD,
    OVERSPEED_THRESHOLD_MPS,
    VEHICLE_IDS,
    ZONES,
)
from app.models import (
    Anomaly,
    MaintenanceRecord,
    Mission,
    TelemetryEvent,
    VehicleCurrentState,
    ZoneCount,
)


async def seed_database(session: AsyncSession) -> None:
    for zone_id in ZONES:
        existing = await session.get(ZoneCount, zone_id)
        if existing is None:
            session.add(ZoneCount(zone_id=zone_id, entry_count=0))

    now = datetime.now(UTC)
    for vehicle_id in VEHICLE_IDS:
        existing = await session.get(VehicleCurrentState, vehicle_id)
        if existing is None:
            session.add(
                VehicleCurrentState(
                    vehicle_id=vehicle_id,
                    last_seen=now,
                    status="idle",
                    battery_pct=100.0,
                    speed_mps=0.0,
                    lat=37.41,
                    lon=-122.08,
                    last_zone=None,
                )
            )
            session.add(Mission(vehicle_id=vehicle_id, status="active"))

    await session.commit()


def detect_anomalies(event: TelemetryEvent) -> list[tuple[str, str]]:
    detected: list[tuple[str, str]] = []

    if event.battery_pct < LOW_BATTERY_THRESHOLD:
        detected.append(
            (
                "low_battery",
                f"Battery at {event.battery_pct}% (threshold {LOW_BATTERY_THRESHOLD}%)",
            )
        )

    if event.speed_mps > OVERSPEED_THRESHOLD_MPS:
        detected.append(
            (
                "overspeed",
                f"Speed {event.speed_mps} m/s exceeds {OVERSPEED_THRESHOLD_MPS} m/s",
            )
        )

    if event.status == "fault":
        detected.append(("fault_state", "Vehicle reported fault status"))

    if event.error_codes:
        detected.append(("error_codes", f"Error codes: {', '.join(event.error_codes)}"))

    return detected


async def increment_zone_count(session: AsyncSession, zone_id: str) -> None:
    # UPDATE zone_counts
    # SET entry_count = entry_count + 1, updated_at = now()
    # WHERE zone_id = :zone_id
    await session.execute(
        update(ZoneCount)
        .where(ZoneCount.zone_id == zone_id)
        .values(entry_count=ZoneCount.entry_count + 1, updated_at=func.now())
    )


async def handle_fault_transition(
    session: AsyncSession,
    vehicle_id: str,
    previous_status: str | None,
    new_status: str,
    reason: str,
) -> tuple[bool, int | None]:
    if new_status != "fault" or previous_status == "fault":
        return False, None

    result = await session.execute(
        select(Mission)
        .where(Mission.vehicle_id == vehicle_id, Mission.status == "active")
        .with_for_update()
    )
    active_mission = result.scalar_one_or_none()

    if active_mission is None:
        return False, None

    existing_maintenance = await session.execute(
        select(MaintenanceRecord)
        .where(MaintenanceRecord.mission_id == active_mission.id)
        .limit(1)
    )
    existing_record = existing_maintenance.scalar_one_or_none()
    if existing_record is not None:
        return True, existing_record.id

    active_mission.status = "cancelled"
    active_mission.cancelled_at = datetime.now(UTC)
    record = MaintenanceRecord(
        vehicle_id=vehicle_id,
        mission_id=active_mission.id,
        reason=reason,
    )
    session.add(record)
    await session.flush()

    return True, record.id


async def get_fleet_aggregate(session: AsyncSession) -> dict[str, int]:
    result = await session.execute(
        select(VehicleCurrentState.status, func.count()).group_by(
            VehicleCurrentState.status
        )
    )
    counts = {"idle": 0, "moving": 0, "charging": 0, "fault": 0}
    for status, count in result.all():
        if status in counts:
            counts[status] = count
    return counts


async def get_latest_anomaly_per_vehicle(session: AsyncSession) -> dict[str, Anomaly]:
    subq = (
        select(
            Anomaly.vehicle_id,
            func.max(Anomaly.detected_at).label("max_detected_at"),
        )
        .group_by(Anomaly.vehicle_id)
        .subquery()
    )
    result = await session.execute(
        select(Anomaly).join(
            subq,
            (Anomaly.vehicle_id == subq.c.vehicle_id)
            & (Anomaly.detected_at == subq.c.max_detected_at),
        )
    )
    return {row.vehicle_id: row for row in result.scalars().all()}
