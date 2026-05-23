from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.constants import VALID_STATUSES, ZONES


class TelemetryIn(BaseModel):
    vehicle_id: str
    timestamp: datetime
    lat: float
    lon: float
    battery_pct: float = Field(ge=0, le=100)
    speed_mps: float = Field(ge=0)
    status: str
    error_codes: list[str] = Field(default_factory=list)
    zone_entered: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
        return value

    @field_validator("zone_entered")
    @classmethod
    def validate_zone(cls, value: str | None) -> str | None:
        if value is not None and value not in ZONES:
            raise ValueError("zone_entered must be one of the known zones or null")
        return value


class TelemetryResponse(BaseModel):
    id: int
    vehicle_id: str
    timestamp: datetime
    status: str
    anomalies_detected: list[str]


class VehicleStateOut(BaseModel):
    vehicle_id: str
    last_seen: datetime
    status: str
    battery_pct: float
    speed_mps: float
    lat: float
    lon: float
    last_zone: str | None
    latest_anomaly: "AnomalyOut | None" = None


class AnomalyOut(BaseModel):
    id: int
    vehicle_id: str
    anomaly_type: str
    message: str
    detected_at: datetime


class FleetAggregateOut(BaseModel):
    idle: int = 0
    moving: int = 0
    charging: int = 0
    fault: int = 0


class ZoneCountOut(BaseModel):
    zone_id: str
    entry_count: int
    updated_at: datetime | None = None


class StatusUpdateIn(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
        return value


class StatusUpdateOut(BaseModel):
    vehicle_id: str
    status: str
    mission_cancelled: bool
    maintenance_record_id: int | None = None


VehicleStateOut.model_rebuild()
