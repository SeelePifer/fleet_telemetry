from datetime import datetime

import pytest
from pydantic import ValidationError

from app.constants import LOW_BATTERY_THRESHOLD, OVERSPEED_THRESHOLD_MPS, UTC, ZONES
from app.schemas import StatusUpdateIn, TelemetryIn


def test_telemetry_in_accepts_valid_payload() -> None:
    payload = TelemetryIn(
        vehicle_id="v-01",
        timestamp=datetime.now(UTC),
        lat=37.41,
        lon=-122.08,
        battery_pct=78,
        speed_mps=1.2,
        status="moving",
        error_codes=[],
        zone_entered="inbound_dock_a",
    )
    assert payload.vehicle_id == "v-01"
    assert payload.zone_entered in ZONES


def test_telemetry_in_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        TelemetryIn(
            vehicle_id="v-01",
            timestamp=datetime.now(UTC),
            lat=37.41,
            lon=-122.08,
            battery_pct=78,
            speed_mps=1.2,
            status="exploded",
            error_codes=[],
        )


def test_telemetry_in_rejects_unknown_zone() -> None:
    with pytest.raises(ValidationError):
        TelemetryIn(
            vehicle_id="v-01",
            timestamp=datetime.now(UTC),
            lat=37.41,
            lon=-122.08,
            battery_pct=78,
            speed_mps=1.2,
            status="moving",
            zone_entered="unknown_zone",
        )


def test_telemetry_in_rejects_battery_out_of_range() -> None:
    with pytest.raises(ValidationError):
        TelemetryIn(
            vehicle_id="v-01",
            timestamp=datetime.now(UTC),
            lat=37.41,
            lon=-122.08,
            battery_pct=150,
            speed_mps=1.2,
            status="moving",
        )


def test_telemetry_in_rejects_negative_speed() -> None:
    with pytest.raises(ValidationError):
        TelemetryIn(
            vehicle_id="v-01",
            timestamp=datetime.now(UTC),
            lat=37.41,
            lon=-122.08,
            battery_pct=50,
            speed_mps=-1,
            status="moving",
        )


def test_status_update_in_accepts_fault() -> None:
    payload = StatusUpdateIn(status="fault")
    assert payload.status == "fault"


def test_anomaly_threshold_constants() -> None:
    assert LOW_BATTERY_THRESHOLD == 15
    assert OVERSPEED_THRESHOLD_MPS == 5.0
