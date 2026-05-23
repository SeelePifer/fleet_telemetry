import { FleetSummary, VehicleTable, ZoneCounts } from "./components/Dashboard";
import { useFleetData } from "./hooks/useFleetData";
import "./App.css";

export default function App() {
  const { snapshot, connected, error } = useFleetData();

  return (
    <div className="app">
      <header>
        <h1>Fleet Telemetry Dashboard</h1>
        <div className="header-meta">
          <span className={`conn ${connected ? "online" : "offline"}`}>
            {connected ? "Live (WebSocket)" : "Reconnecting…"}
          </span>
          {error && <span className="error">{error}</span>}
        </div>
      </header>
      <main>
        <FleetSummary aggregate={snapshot.aggregate} />
        <div className="grid-2">
          <VehicleTable vehicles={snapshot.vehicles} />
          <ZoneCounts zones={snapshot.zones} />
        </div>
      </main>
    </div>
  );
}
