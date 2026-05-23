import type { FleetAggregate, Vehicle, ZoneCount } from "../types";

const statusColors: Record<string, string> = {
  idle: "#64748b",
  moving: "#22c55e",
  charging: "#3b82f6",
  fault: "#ef4444",
};

export function FleetSummary({ aggregate }: { aggregate: FleetAggregate }) {
  const entries = Object.entries(aggregate) as [keyof FleetAggregate, number][];
  return (
    <section className="panel summary">
      <h2>Fleet Status</h2>
      <div className="summary-grid">
        {entries.map(([status, count]) => (
          <div key={status} className="summary-card" style={{ borderColor: statusColors[status] }}>
            <span className="summary-label">{status}</span>
            <span className="summary-count">{count}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

export function VehicleTable({ vehicles }: { vehicles: Vehicle[] }) {
  return (
    <section className="panel">
      <h2>Vehicles ({vehicles.length})</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Status</th>
              <th>Battery</th>
              <th>Speed</th>
              <th>Zone</th>
              <th>Latest Anomaly</th>
            </tr>
          </thead>
          <tbody>
            {vehicles.map((v) => (
              <tr key={v.vehicle_id}>
                <td>{v.vehicle_id}</td>
                <td>
                  <span className="badge" style={{ background: statusColors[v.status] ?? "#999" }}>
                    {v.status}
                  </span>
                </td>
                <td>
                  <div className="battery-bar">
                    <div
                      className="battery-fill"
                      style={{
                        width: `${v.battery_pct}%`,
                        background: v.battery_pct < 15 ? "#ef4444" : "#22c55e",
                      }}
                    />
                    <span>{v.battery_pct.toFixed(0)}%</span>
                  </div>
                </td>
                <td>{v.speed_mps.toFixed(1)} m/s</td>
                <td>{v.last_zone ?? "—"}</td>
                <td className="anomaly-cell">
                  {v.latest_anomaly ? (
                    <>
                      <strong>{v.latest_anomaly.anomaly_type}</strong>
                      <span>{v.latest_anomaly.message}</span>
                    </>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function ZoneCounts({ zones }: { zones: ZoneCount[] }) {
  const max = Math.max(...zones.map((z) => z.entry_count), 1);
  return (
    <section className="panel">
      <h2>Zone Entry Counts</h2>
      <ul className="zone-list">
        {zones.map((z) => (
          <li key={z.zone_id}>
            <span className="zone-name">{z.zone_id}</span>
            <div className="zone-bar-wrap">
              <div className="zone-bar" style={{ width: `${(z.entry_count / max) * 100}%` }} />
            </div>
            <span className="zone-count">{z.entry_count}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
