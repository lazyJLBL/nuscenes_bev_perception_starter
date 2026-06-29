# CARLA BEV Perception Sandbox Platform

Current version: **Batch 4: CARLA multi-scenario admin management**.

The platform now uses CARLA scenario language in the database and admin console. Admin users can manage CARLA Town scenarios with weather, traffic, duration, spawn point, and synchronous-mode settings. The backend CARLA runner from Batch 3 remains available through `/api/carla/*`.

## Current Capabilities

- MySQL-backed platform:
  - users,
  - model catalog,
  - CARLA/nuScenes scenario templates,
  - simulation runs,
  - run artifacts.
- Admin console:
  - create/edit models,
  - create/edit CARLA scenarios,
  - configure Town, weather, traffic, walkers, duration, spawn point, sync mode.
- Client views:
  - sandbox page,
  - experiment history,
  - system status.
- CARLA tools:
  - installer,
  - environment checker,
  - FastAPI runtime service.
- Existing nuScenes offline workflow remains available as fallback.

## CARLA Scenario Defaults

Database seed data creates four active CARLA scenarios:

| Scenario | Town | Purpose |
|---|---|---|
| Town01 Basic Drive | `Town01` | simple smoke test |
| Town03 Urban Traffic | `Town03` | moderate client demo |
| Town05 Junction Stress | `Town05` | junction-heavy checks |
| Town10HD Dense City | `Town10HD` | richer visual validation |

Legacy Unity placeholder scenarios are marked `disabled`. They are not deleted, so old records remain inspectable.

## Requirements

- Windows 10/11
- Python 3.8+
- Node.js 18+
- MySQL 8.0
- PowerShell
- CARLA 0.9.15 Windows package
- At least 55GB free disk space if Additional Maps are installed

Install dependencies:

```bash
pip install -r requirements.txt
npm install --prefix frontend
```

## Environment

MySQL:

```powershell
$env:DATABASE_URL="mysql+pymysql://root:0000@localhost:3306/nuscenes_bev_platform?charset=utf8mb4"
```

CARLA:

```powershell
$env:CARLA_HOME="D:\CARLA\CARLA_0.9.15"
$env:CARLA_HOST="127.0.0.1"
$env:CARLA_PORT="2000"
```

Initialize or upgrade the database schema:

```powershell
python - <<'PY'
from backend.db import create_schema
create_schema(seed=True)
print("database ready")
PY
```

The schema upgrade adds `simulation_scenarios.carla_town` when needed and seeds CARLA scenarios.

## Install CARLA

Dry run:

```powershell
.\scripts\install_carla_0915.ps1 -DryRun
```

Install base simulator:

```powershell
.\scripts\install_carla_0915.ps1 -SkipAdditionalMaps
```

Install base simulator and Additional Maps:

```powershell
.\scripts\install_carla_0915.ps1
```

Check the local environment:

```powershell
python scripts/check_carla_environment.py
```

## Start Platform

Backend:

```powershell
$env:DATABASE_URL="mysql+pymysql://root:0000@localhost:3306/nuscenes_bev_platform?charset=utf8mb4"
$env:CARLA_HOME="D:\CARLA\CARLA_0.9.15"
python -m backend.main
```

Frontend:

```powershell
npm run dev
```

Open:

- frontend: `http://127.0.0.1:5174`
- admin console: `http://127.0.0.1:5174/admin`
- database status: `http://127.0.0.1:8010/api/db/status`
- CARLA status: `http://127.0.0.1:8010/api/carla/status`

## Admin Workflow

1. Open `/admin`.
2. Click "Initialize" to ensure the MySQL schema and seed data are current.
3. Edit or add models in the model catalog.
4. Edit or add CARLA scenarios:
   - `dataset_source`: `carla`
   - `carla_town`: `Town01`, `Town03`, `Town05`, `Town10HD`, etc.
   - `default_config_json`:

```json
{
  "duration_seconds": 15,
  "weather": "ClearNoon",
  "traffic_vehicles": 20,
  "traffic_walkers": 5,
  "ego_vehicle": "vehicle.tesla.model3",
  "spawn_point_index": 0,
  "synchronous_mode": true
}
```

## CARLA API

```text
GET  /api/carla/status
POST /api/carla/start
POST /api/carla/stop
GET  /api/carla/maps
POST /api/carla/run
```

Run a CARLA scenario directly:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8010/api/carla/run `
  -ContentType "application/json" `
  -Body '{"town":"Town03","duration_seconds":10,"traffic_vehicles":10,"traffic_walkers":0}'
```

Outputs:

```text
outputs/carla/<run_uid>/trajectory.json
backend/static/carla/<run_uid>/camera.jpg
```

## Product API

```text
GET   /api/db/status
POST  /api/admin/db/init
GET   /api/admin/models
POST  /api/admin/models
PATCH /api/admin/models/{model_id}
GET   /api/admin/scenarios
POST  /api/admin/scenarios
PATCH /api/admin/scenarios/{scenario_id}
GET   /api/client/bootstrap
GET   /api/client/runs
GET   /api/client/runs/{run_id}
POST  /api/client/runs
```

## Validation

Run:

```bash
python -m pytest -q
npm --prefix frontend run build
python scripts/check_carla_environment.py
```

Database smoke check:

```sql
SELECT scenario_key, dataset_source, carla_town, status
FROM simulation_scenarios
ORDER BY id;
```

Batch 4 verification on the development machine:

- Database upgrade/seed: passed
- Unit/API tests: passed
- Frontend build: passed
- Admin page supports CARLA scenario fields

## Next Batch

Batch 5 will make the client sandbox CARLA-first:

- CARLA status panel,
- start button,
- scenario selection,
- CARLA run button,
- camera image and metrics display,
- experiment history with CARLA results.
