from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.telemetry import handle_fault_transition


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


async def test_handle_fault_transition_skips_non_fault_status(
    mock_session: AsyncMock,
) -> None:
    cancelled, maintenance_id = await handle_fault_transition(
        mock_session, "v-01", "moving", "idle", "test"
    )
    assert cancelled is False
    assert maintenance_id is None
    mock_session.execute.assert_not_called()


async def test_handle_fault_transition_skips_already_fault(
    mock_session: AsyncMock,
) -> None:
    cancelled, maintenance_id = await handle_fault_transition(
        mock_session, "v-01", "fault", "fault", "test"
    )
    assert cancelled is False
    assert maintenance_id is None
    mock_session.execute.assert_not_called()


async def test_handle_fault_transition_no_active_mission(
    mock_session: AsyncMock,
) -> None:
    mission_result = MagicMock()
    mission_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mission_result

    cancelled, maintenance_id = await handle_fault_transition(
        mock_session, "v-01", "moving", "fault", "test"
    )
    assert cancelled is False
    assert maintenance_id is None


async def test_handle_fault_transition_cancels_mission_and_creates_maintenance(
    mock_session: AsyncMock,
) -> None:
    mission = MagicMock()
    mission.id = 42
    mission.status = "active"

    mission_result = MagicMock()
    mission_result.scalar_one_or_none.return_value = mission

    maintenance_result = MagicMock()
    maintenance_result.scalar_one_or_none.return_value = None

    mock_session.execute.side_effect = [mission_result, maintenance_result]

    mock_session.flush = AsyncMock()

    cancelled, maintenance_id = await handle_fault_transition(
        mock_session, "v-01", "moving", "fault", "Manual fault"
    )

    assert cancelled is True
    assert mission.status == "cancelled"
    assert mission.cancelled_at is not None
    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()


async def test_handle_fault_transition_returns_existing_maintenance(
    mock_session: AsyncMock,
) -> None:
    mission = MagicMock()
    mission.id = 42

    existing_record = MagicMock()
    existing_record.id = 99

    mission_result = MagicMock()
    mission_result.scalar_one_or_none.return_value = mission

    maintenance_result = MagicMock()
    maintenance_result.scalar_one_or_none.return_value = existing_record

    mock_session.execute.side_effect = [mission_result, maintenance_result]

    cancelled, maintenance_id = await handle_fault_transition(
        mock_session, "v-01", "moving", "fault", "test"
    )

    assert cancelled is True
    assert maintenance_id == 99
    mock_session.add.assert_not_called()
