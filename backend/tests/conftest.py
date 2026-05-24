from datetime import datetime, timezone

UTC = timezone.utc
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.routes import router
from app.db.session import get_db


@pytest.fixture
def mock_db_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
async def api_client(mock_db_session: AsyncMock) -> AsyncClient:
    app = FastAPI()
    app.include_router(router)

    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def make_telemetry_event(**overrides):
    from app.models import TelemetryEvent

    defaults = {
        "id": 1,
        "vehicle_id": "v-01",
        "timestamp": datetime.now(UTC),
        "lat": 37.41,
        "lon": -122.08,
        "battery_pct": 80.0,
        "speed_mps": 1.0,
        "status": "moving",
        "error_codes": [],
        "zone_entered": None,
    }
    defaults.update(overrides)
    return TelemetryEvent(**defaults)
