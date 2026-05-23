# AI Interaction Log

This log documents meaningful AI-assisted work on the Fleet Telemetry take-home project.

---

## Prompt 1 — Full project kickoff

**Prompt (summary):** Build the complete fleet telemetry monitoring service per the take-home spec. Use FastAPI, PostgreSQL, SQLAlchemy async, React dashboard, ADR, and follow pre-planned architecture (snapshot table, atomic zone counters, transactional fault handling, WebSocket dashboard).

**AI output (summary):**
- Scaffolded monorepo: `/backend`, `/frontend`, `/docs`, `docker-compose.yml`
- Implemented FastAPI endpoints: `POST /telemetry`, `GET /zones/counts`, `PATCH /vehicles/{id}/status`, `GET /anomalies`, `GET /fleet/aggregate`, `GET /vehicles`, `WS /ws/fleet`
- PostgreSQL models for telemetry, snapshots, zones, anomalies, missions, maintenance
- React + TypeScript dashboard with WebSocket live updates
- ADR covering Postgres choice, snapshot table, transaction boundaries
- Telemetry simulator script for load testing

**Corrections / redirections:** None yet — initial build.

---

## Prompt 2 — Database setup and first end-to-end test

**Prompt (summary):** Run the stack with Docker; fix PostgreSQL connection errors; validate the system point-to-point.

**What we observed:**
- First failure looked like a credentials problem (`FATAL: password authentication failed for user "fleet"`), but Postgres inside Docker was healthy (`pg_isready`, queries from inside the container worked).
- Root cause on Windows: **port 5432 on the host was not reaching the compose DB** (local/WSL Postgres intercepting `localhost:5432`). Fix: map DB to host port **5433** and update local `DATABASE_URL` defaults.
- After that, basic E2E passed: API health, `POST /telemetry`, zone counts incrementing, dashboard on `:5173`, simulator sending ~4000 events.

**Concurrency gap (not visible yet):** At this stage we confirmed the app *worked*, but we had **not** stress-tested or reasoned about race conditions. The simulator reported success; zone counters and fault states looked correct under casual load. The dangerous scenarios (duplicate fault handling, concurrent ingests on the same vehicle) were not exercised.

**Corrections / redirections:** Treat “auth failed” as an environment/routing issue first, not schema/password. Do not equate “simulator finished OK” with “concurrency invariants proven.”

---

## Prompt 3 — Architecture review: concurrency, SQL, and fault transition

**Prompt (summary):** Explain where atomic SQL updates and fault-transition locking live; validate whether the design matches `FOR UPDATE` + single transaction + no double maintenance.

**What we learned by reading the code together:**
- **Zone counters** were already correct: single-statement `UPDATE zone_counts SET entry_count = entry_count + 1` (no read-modify-write in Python).
- **Fault transition** had `SELECT … FOR UPDATE` on `missions` where `status = 'active'`, plus an application guard (`previous_status == 'fault'`).
- **Initial solution was incomplete:**
  - `ingest_telemetry` read `vehicle_current_state` **without** row lock, while `PATCH /status` already used `FOR UPDATE` on the vehicle.
  - The guard on `previous_status` is taken from memory at request start; under concurrent fault events two transactions could both believe they are “entering fault” until the mission lock serializes them — mission lock helped, but vehicle state was still racy.
  - No DB-level guarantee against two active missions or two maintenance rows per mission.
  - No idempotency for HTTP retries (would double-count zones and duplicate events, not just fault side effects).

**Corrections / redirections:** The first implementation was *directionally* right (Postgres + transactions + mission `FOR UPDATE`) but **not adequate** for the exercise’s hardest requirement until we added defense in depth.

---

## Prompt 4 — Iterate the architecture (hardening pass)

**Prompt (summary):** Implement the discussed improvements.

**Changes made:**
1. **`FOR UPDATE` on vehicle** in `ingest_telemetry` (same pattern as PATCH), via `_get_vehicle_for_update()`.
2. **Partial unique indexes** (startup DDL):
   - one `active` mission per `vehicle_id`
   - one `maintenance_records` row per `mission_id`
3. **Idempotency-Key** header on `POST /telemetry` and `PATCH /vehicles/{id}/status`:
   - `pg_advisory_xact_lock(hashtext(key))` + `processed_idempotency_keys` table
   - safe replays on network retries
4. **Extra check** in `handle_fault_transition`: if maintenance already exists for the mission, return existing id instead of inserting again.
5. **ADR expanded** with full SQL catalog, lock types, transaction diagram, and Postgres rationale.

**Corrections / redirections:** Concurrency fixes belong in three layers — application locks, atomic SQL, and schema constraints — not just one.

---

## Prompt 5 — How we tested the final design

**Procedure we followed:**

| Step | Action | What it validated |
|------|--------|-------------------|
| 1 | `docker compose up --build` | Full stack, backend → `db:5432`, host DB on `:5433` |
| 2 | `GET /fleet/aggregate`, `POST /telemetry` with `zone_entered` | Ingest + atomic zone increment |
| 3 | Simulator inside backend container (~4000 events) | Sustained writes, dashboard WebSocket |
| 4 | `PATCH /vehicles/v-06/status` → `fault` with `Idempotency-Key` | Fault workflow on vehicle with **active** mission |
| 5 | Repeat same PATCH with **same** idempotency key | Same `maintenance_record_id`, no duplicate row |
| 6 | SQL checks on port 5433 | `missions.status = cancelled`, `COUNT(*) maintenance_records = 1`, indexes `uq_*` present |

**Example verification queries:**

```sql
SELECT status, cancelled_at IS NOT NULL FROM missions WHERE vehicle_id = 'v-06';
SELECT COUNT(*) FROM maintenance_records WHERE vehicle_id = 'v-06';
SELECT indexname FROM pg_indexes WHERE indexname LIKE 'uq_%';
```

**Corrections / redirections:** Use a vehicle known to still have `status = 'active'` in `missions`; many simulator runs had already cancelled missions, which made early fault tests look like “no-op” (`mission_cancelled: false`) even though the code path was correct.

---

## Prompt 6 — CI and repo hygiene

**Prompt (summary):** GitHub Actions to lint/build (no deploy); `.gitignore` for caches and local artifacts.

**AI output (summary):**
- Modular workflows: `ci.yml` → backend (Ruff + compile + import), frontend (`tsc` + `vite build`), Docker build without push
- `.gitignore` for Python/Node caches, `.env`, `pgdata/`, IDE/OS noise; keep `package-lock.json` tracked

---

## Reflection

- **Good at:** Scaffolding quickly, translating concurrency requirements into SQL patterns once the gap was named, and documenting the final design in ADR form.
- **Where the first version fell short:** We shipped plausible Postgres patterns early (`FOR UPDATE` on missions, atomic zone `UPDATE`) but **did not initially prove** concurrent invariants end-to-end. Casual simulator success masked missing vehicle row locks, missing unique indexes, and missing HTTP idempotency.
- **What changed our understanding:** Stepping through the fault workflow SQL by SQL (as in a design review), then **re-testing with idempotency keys and DB inspection**, not only HTTP 200 responses.
- **Manual double-check still worth doing:** Two parallel fault requests for the same vehicle (e.g. `curl` in background + PATCH), concurrent `POST /telemetry` with the same zone from multiple clients, and confirming zone count equals expected entries under deliberate contention.
- **Recommendation for reviewers:** Read ADR §2–§5 (SQL catalog + locks + constraints), then run Prompt 5’s test table against a fresh compose volume.
