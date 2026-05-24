# Fleet Telemetry Monitoring Service

Vertical slice of a fleet monitoring system: ingest telemetry from 50 autonomous vehicles, detect anomalies, count zone traversals under concurrency, and display live fleet state.

## Stack

- **Backend:** FastAPI, SQLAlchemy 2.0 async, PostgreSQL, WebSocket
- **Frontend:** React, TypeScript, Vite
- **Docs:** [ADR](docs/ADR.md), [AI Interaction Log](docs/AI_LOG.md)

## Quick start (Docker)

```bash
docker compose up --build
```

- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:5173

## Local development (without Docker)

### 1. PostgreSQL

Start Postgres locally (or use Docker for DB only):

```bash
docker run -d --name fleet-pg -e POSTGRES_USER=fleet -e POSTGRES_PASSWORD=fleet -e POSTGRES_DB=fleet_telemetry -p 5433:5432 postgres:16-alpine
```

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
set DATABASE_URL=postgresql+asyncpg://fleet:fleet@localhost:5433/fleet_telemetry
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### 4. Simulate telemetry load

With the backend running:

```bash
cd backend
pip install httpx
python scripts/simulate_telemetry.py
```

Or from the `scripts` folder:

```bash
cd backend/scripts
pip install httpx
python simulate_telemetry.py
```

## Tests

### Backend (pytest)

```bash
cd backend
pip install -r requirements-dev.txt
pytest -v
```

### Frontend (Vitest)

```bash
cd frontend
npm install
npm run test
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/telemetry` | Ingest telemetry event |
| GET | `/zones/counts` | Per-zone entry counts |
| PATCH | `/vehicles/{vehicle_id}/status` | Update vehicle status (fault → cancel mission + maintenance) |
| GET | `/anomalies` | Query anomalies (`vehicle_id`, `start`, `end`, `limit`) |
| GET | `/fleet/aggregate` | Per-status fleet counts |
| GET | `/vehicles` | All vehicles with latest anomaly |
| WS | `/ws/fleet` | Live fleet snapshots (every 2s) |

## Example telemetry POST

```bash
curl -X POST http://localhost:8000/telemetry \
  -H "Content-Type: application/json" \
  -d "{\"vehicle_id\":\"v-01\",\"timestamp\":\"2026-05-23T12:00:00Z\",\"lat\":37.41,\"lon\":-122.08,\"battery_pct\":78,\"speed_mps\":1.2,\"status\":\"moving\",\"error_codes\":[],\"zone_entered\":null}"
```

## Project structure

```
backend/app/     FastAPI application
frontend/src/    React dashboard
docs/            ADR + AI log
docker-compose.yml
```

## Design notes

See [docs/ADR.md](docs/ADR.md) for PostgreSQL vs SQLite, snapshot table, anomaly rules, fault transaction isolation, and scale-out considerations.
