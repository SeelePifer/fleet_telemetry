export interface Anomaly {
  anomaly_type: string;
  message: string;
  detected_at: string;
}

export interface Vehicle {
  vehicle_id: string;
  status: string;
  battery_pct: number;
  speed_mps: number;
  last_seen: string;
  last_zone: string | null;
  latest_anomaly: Anomaly | null;
}

export interface ZoneCount {
  zone_id: string;
  entry_count: number;
}

export interface FleetAggregate {
  idle: number;
  moving: number;
  charging: number;
  fault: number;
}

export interface FleetSnapshot {
  aggregate: FleetAggregate;
  vehicles: Vehicle[];
  zones: ZoneCount[];
}
