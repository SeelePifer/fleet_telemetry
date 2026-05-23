import { useEffect, useRef, useState } from "react";
import type { FleetSnapshot } from "../types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/ws/fleet";

const emptySnapshot: FleetSnapshot = {
  aggregate: { idle: 0, moving: 0, charging: 0, fault: 0 },
  vehicles: [],
  zones: [],
};

export function useFleetData() {
  const [snapshot, setSnapshot] = useState<FleetSnapshot>(emptySnapshot);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchInitial() {
      try {
        const [vehiclesRes, aggregateRes, zonesRes] = await Promise.all([
          fetch(`${API_URL}/vehicles`),
          fetch(`${API_URL}/fleet/aggregate`),
          fetch(`${API_URL}/zones/counts`),
        ]);
        if (!vehiclesRes.ok || !aggregateRes.ok || !zonesRes.ok) {
          throw new Error("Failed to load initial fleet data");
        }
        const vehicles = await vehiclesRes.json();
        const aggregate = await aggregateRes.json();
        const zones = await zonesRes.json();
        if (!cancelled) {
          setSnapshot({
            aggregate,
            vehicles: vehicles.map((v: Record<string, unknown>) => ({
              vehicle_id: v.vehicle_id,
              status: v.status,
              battery_pct: v.battery_pct,
              speed_mps: v.speed_mps,
              last_seen: String(v.last_seen),
              last_zone: v.last_zone as string | null,
              latest_anomaly: v.latest_anomaly
                ? {
                    anomaly_type: (v.latest_anomaly as Record<string, string>).anomaly_type,
                    message: (v.latest_anomaly as Record<string, string>).message,
                    detected_at: (v.latest_anomaly as Record<string, string>).detected_at,
                  }
                : null,
            })),
            zones: zones.map((z: Record<string, unknown>) => ({
              zone_id: z.zone_id,
              entry_count: z.entry_count,
            })),
          });
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unknown error");
        }
      }
    }

    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setError(null);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "fleet_snapshot") {
          setSnapshot(data.payload);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        if (!cancelled) {
          retryRef.current = setTimeout(connect, 2000);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    fetchInitial();
    connect();

    return () => {
      cancelled = true;
      if (retryRef.current) clearTimeout(retryRef.current);
      wsRef.current?.close();
    };
  }, []);

  return { snapshot, connected, error };
}
