from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

UTC = timezone.utc


async def test_post_telemetry_validation_error(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/telemetry",
        json={
            "vehicle_id": "v-01",
            "timestamp": datetime.now(UTC).isoformat(),
            "lat": 37.41,
            "lon": -122.08,
            "battery_pct": 78,
            "speed_mps": 1.2,
            "status": "invalid_status",
            "error_codes": [],
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    mock_conn = AsyncMock()
    mock_conn.run_sync = AsyncMock()

    mock_begin = AsyncMock()
    mock_begin.__aenter__.return_value = mock_conn
    mock_begin.__aexit__.return_value = None

    mock_task = MagicMock()
    mock_task.cancel = MagicMock()

    with (
        patch("app.main.engine") as mock_engine,
        patch("app.main.seed_database", new_callable=AsyncMock),
        patch("app.main.ensure_db_constraints", new_callable=AsyncMock),
        patch("app.main.asyncio.create_task", return_value=mock_task),
    ):
        mock_engine.begin.return_value = mock_begin
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
