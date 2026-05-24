import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import App from "./App";

vi.mock("./hooks/useFleetData", () => ({
  useFleetData: () => ({
    snapshot: {
      aggregate: { idle: 1, moving: 2, charging: 0, fault: 0 },
      vehicles: [
        {
          vehicle_id: "v-01",
          status: "moving",
          battery_pct: 80,
          speed_mps: 1.5,
          last_seen: "2026-05-24T12:00:00Z",
          last_zone: "aisle_a",
          latest_anomaly: null,
        },
      ],
      zones: [{ zone_id: "aisle_a", entry_count: 5 }],
    },
    connected: true,
    error: null,
  }),
}));

describe("App", () => {
  it("renders dashboard header and live status", () => {
    render(<App />);

    expect(screen.getByText("Fleet Telemetry Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Live (WebSocket)")).toBeInTheDocument();
    expect(screen.getByText("v-01")).toBeInTheDocument();
  });
});
