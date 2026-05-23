import asyncio
import random
from datetime import UTC, datetime

import httpx

API_URL = "http://localhost:8000"
VEHICLE_IDS = [f"v-{i:02d}" for i in range(1, 51)]
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
STATUSES = ["idle", "moving", "charging", "fault"]


async def send_event(client: httpx.AsyncClient, vehicle_id: str) -> None:
    zone_entered = random.choice(ZONES) if random.random() < 0.05 else None
    status = random.choices(STATUSES, weights=[20, 60, 15, 5])[0]
    payload = {
        "vehicle_id": vehicle_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "lat": 37.41 + random.uniform(-0.01, 0.01),
        "lon": -122.08 + random.uniform(-0.01, 0.01),
        "battery_pct": random.uniform(5, 100),
        "speed_mps": random.uniform(0, 7),
        "status": status,
        "error_codes": random.choice([[], [], ["E001"], ["E002", "E003"]]),
        "zone_entered": zone_entered,
    }
    resp = await client.post(f"{API_URL}/telemetry", json=payload, timeout=10)
    resp.raise_for_status()


async def main() -> None:
    async with httpx.AsyncClient() as client:
        for _ in range(200):
            tasks = [send_event(client, random.choice(VEHICLE_IDS)) for _ in range(20)]
            await asyncio.gather(*tasks)
            await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())
