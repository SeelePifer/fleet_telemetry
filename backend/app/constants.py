from datetime import timezone

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc  # Python 3.10 compatibility

ZONES = [
    "inbound_dock_a",
    "inbound_dock_b",
    "receiving_staging",
    "aisle_a",
    "aisle_b",
    "aisle_c",
    "high_bay_1",
    "high_bay_2",
    "bulk_storage",
    "pick_zone_1",
    "pick_zone_2",
    "pack_station",
    "sort_belt",
    "outbound_dock_a",
    "outbound_dock_b",
    "shipping_staging",
    "charging_bay_1",
    "charging_bay_2",
    "charging_bay_3",
    "maintenance_bay",
]

VEHICLE_IDS = [f"v-{i:02d}" for i in range(1, 51)]

VALID_STATUSES = {"idle", "moving", "charging", "fault"}

ANOMALY_TYPES = {
    "low_battery",
    "overspeed",
    "fault_state",
    "stale_telemetry",
    "error_codes",
}

LOW_BATTERY_THRESHOLD = 15
OVERSPEED_THRESHOLD_MPS = 5.0
STALE_TELEMETRY_SECONDS = 10
