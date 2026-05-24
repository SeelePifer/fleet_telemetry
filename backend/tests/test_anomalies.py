from tests.conftest import make_telemetry_event

from app.services.telemetry import detect_anomalies


def test_detect_anomalies_returns_empty_for_normal_event() -> None:
    event = make_telemetry_event(
        battery_pct=80, speed_mps=2, status="moving", error_codes=[]
    )
    assert detect_anomalies(event) == []


def test_detect_anomalies_low_battery() -> None:
    event = make_telemetry_event(battery_pct=10, speed_mps=1, status="moving")
    anomalies = detect_anomalies(event)
    assert len(anomalies) == 1
    assert anomalies[0][0] == "low_battery"
    assert "10" in anomalies[0][1]


def test_detect_anomalies_overspeed() -> None:
    event = make_telemetry_event(battery_pct=80, speed_mps=6.5, status="moving")
    anomalies = detect_anomalies(event)
    assert any(a[0] == "overspeed" for a in anomalies)


def test_detect_anomalies_fault_state() -> None:
    event = make_telemetry_event(status="fault")
    anomalies = detect_anomalies(event)
    assert any(a[0] == "fault_state" for a in anomalies)


def test_detect_anomalies_error_codes() -> None:
    event = make_telemetry_event(error_codes=["E001", "E002"])
    anomalies = detect_anomalies(event)
    assert any(a[0] == "error_codes" for a in anomalies)
    assert "E001" in anomalies[0][1]


def test_detect_anomalies_multiple_at_once() -> None:
    event = make_telemetry_event(
        battery_pct=5,
        speed_mps=7,
        status="fault",
        error_codes=["E001"],
    )
    types = {a[0] for a in detect_anomalies(event)}
    assert types == {"low_battery", "overspeed", "fault_state", "error_codes"}
