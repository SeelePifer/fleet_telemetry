import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FleetSummary, VehicleTable, ZoneCounts } from "../components/Dashboard";
import type { FleetAggregate, Vehicle, ZoneCount } from "../types";

const aggregate: FleetAggregate = {
  idle: 10,
  moving: 25,
  charging: 10,
  fault: 5,
};

const vehicles: Vehicle[] = [
  {
    vehicle_id: "v-01",
    status: "moving",
    battery_pct: 78,
    speed_mps: 2.5,
    last_seen: "2026-05-24T12:00:00Z",
    last_zone: "aisle_a",
    latest_anomaly: {
      anomaly_type: "overspeed",
      message: "Speed 6 m/s exceeds 5 m/s",
      detected_at: "2026-05-24T12:00:00Z",
    },
  },
  {
    vehicle_id: "v-02",
    status: "idle",
    battery_pct: 90,
    speed_mps: 0,
    last_seen: "2026-05-24T12:00:00Z",
    last_zone: null,
    latest_anomaly: null,
  },
];

const zones: ZoneCount[] = [
  { zone_id: "aisle_a", entry_count: 12 },
  { zone_id: "inbound_dock_a", entry_count: 3 },
];

describe("FleetSummary", () => {
  it("renders fleet status counts", () => {
    render(<FleetSummary aggregate={aggregate} />);

    expect(screen.getByText("Fleet Status")).toBeInTheDocument();
    expect(screen.getByText("idle")).toBeInTheDocument();
    expect(screen.getByText("moving")).toBeInTheDocument();
    expect(screen.getByText("25")).toBeInTheDocument();
    expect(screen.getByText("fault")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });
});

describe("VehicleTable", () => {
  it("renders vehicle rows and latest anomaly", () => {
    render(<VehicleTable vehicles={vehicles} />);

    expect(screen.getByText("Vehicles (2)")).toBeInTheDocument();
    expect(screen.getByText("v-01")).toBeInTheDocument();
    expect(screen.getByText("overspeed")).toBeInTheDocument();
    expect(screen.getByText("Speed 6 m/s exceeds 5 m/s")).toBeInTheDocument();
    expect(screen.getByText("v-02")).toBeInTheDocument();
  });

  it("shows dash when vehicle has no anomaly", () => {
    render(<VehicleTable vehicles={[vehicles[1]]} />);
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });
});

describe("ZoneCounts", () => {
  it("renders zone entry counts", () => {
    render(<ZoneCounts zones={zones} />);

    expect(screen.getByText("Zone Entry Counts")).toBeInTheDocument();
    expect(screen.getByText("aisle_a")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("inbound_dock_a")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });
});
