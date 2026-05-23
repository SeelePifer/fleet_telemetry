from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

CONSTRAINT_DDL = (
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_missions_one_active_per_vehicle
    ON missions (vehicle_id)
    WHERE status = 'active'
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_maintenance_one_per_mission
    ON maintenance_records (mission_id)
    WHERE mission_id IS NOT NULL
    """,
)


async def ensure_db_constraints(conn: AsyncConnection) -> None:
    for ddl in CONSTRAINT_DDL:
        await conn.execute(text(ddl))
