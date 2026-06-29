# CARLA BEV Perception Sandbox Platform

Current version: **Batch 5: complete CARLA sandbox workflow**.

This project is a CARLA-based autonomous-driving simulation sandbox with a FastAPI backend, Vue frontend, MySQL persistence, admin scenario management, and client-facing CARLA run results. The original nuScenes offline workflow is retained as a fallback and learning baseline.

## What You Can Do

- Install and check CARLA 0.9.15 on Windows.
- Start CARLA from the backend API.
- Manage CARLA scenarios in the admin console.
- Run CARLA simulations from the client sandbox.
- See camera screenshots, trajectory frames, speed, distance, collision count, and run history.
- Store runs and artifacts in MySQL.
- Continue using the existing nuScenes offline sandbox when CARLA is unavailable.

## Architecture

```text
Vue 3 frontend
  /                  CARLA-first sandbox plus nuScenes fallback
  /experiments       client run history
  /admin             model and CARLA scenario management
  /system            backend health

FastAPI backend
  /api/carla/*       CARLA runtime service
  /api/admin/*       admin model/scenario CRUD
  /api/client/*      client bootstrap and run records
  /api/run_sandbox   existing nuScenes offline run

MySQL
  app_users
  model_catalog
  simulation_scenarios
  simulation_runs
  simulation_run_artifacts

Artifacts
  outputs/carla/<run_uid>/trajectory.json
  backend/static/carla/<run_uid>/camera.jpg
```

## Requirements

- Windows 10/11
- Python 3.8+
- Node.js 18+
- MySQL 8.0
- PowerShell
- CARLA 0.9.15 Windows package
- At least 55GB free disk space if Additional Maps are installed
- NVIDIA GPU recommended

Install project dependencies:

```bash
pip install -r requirements.txt
npm install --prefix frontend
```

## Configure Environment

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

Do not commit real passwords or local `.env` files.

## Install CARLA 0.9.15

Preview the install plan:

```powershell
.\scripts\install_carla_0915.ps1 -DryRun
```

Install the base simulator:

```powershell
.\scripts\install_carla_0915.ps1 -SkipAdditionalMaps
```

Install the base simulator plus Additional Maps:

```powershell
.\scripts\install_carla_0915.ps1
```

The script downloads official CARLA 0.9.15 Windows packages from:

```text
https://tiny.carla.org/carla-0-9-15-windows
https://tiny.carla.org/additional-maps-0-9-15-windows
```

CARLA is installed outside the git repository under:

```text
D:\CARLA\CARLA_0.9.15
```

Check the installation:

```powershell
python scripts/check_carla_environment.py
```

## Initialize Database

Create database:

```sql
CREATE DATABASE IF NOT EXISTS nuscenes_bev_platform
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

Create or upgrade schema and seed data:

```powershell
python - <<'PY'
from backend.db import create_schema
create_schema(seed=True)
print("database ready")
PY
```

Seeded CARLA scenarios:

- `Town01 Basic Drive`
- `Town03 Urban Traffic`
- `Town05 Junction Stress`
- `Town10HD Dense City`

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
- experiment history: `http://127.0.0.1:5174/experiments`
- backend health: `http://127.0.0.1:8010/api/health`
- CARLA status: `http://127.0.0.1:8010/api/carla/status`

## Client Workflow

1. Open `http://127.0.0.1:5174`.
2. Check the CARLA status badge.
3. Click "启动 CARLA" if the simulator is not running.
4. Select a CARLA scenario.
5. Click "运行 CARLA 仿真".
6. Review:
   - RGB camera screenshot,
   - run UID,
   - distance,
   - collision count,
   - average speed,
   - trajectory replay.
7. Open `/experiments` to see the saved run.

If CARLA is not installed, the page shows a readable error and the nuScenes offline sandbox remains available below.

## Admin Workflow

1. Open `/admin`.
2. Click "初始化" to prepare MySQL schema and seed data.
3. Manage model catalog entries.
4. Manage CARLA scenarios:

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

Use `dataset_source=carla` and `carla_town=Town03` or another installed map.

## API Reference

CARLA runtime:

```text
GET  /api/carla/status
POST /api/carla/start
POST /api/carla/stop
GET  /api/carla/maps
POST /api/carla/run
```

Product API:

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

nuScenes fallback:

```text
GET  /api/modules
GET  /api/experiments
POST /api/run_sandbox
POST /api/inference/{model_id}
```

## Validation

Run:

```bash
python -m pytest -q
npm --prefix frontend run build
python scripts/check_carla_environment.py
```

CARLA smoke test after installation:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8010/api/carla/start `
  -ContentType "application/json" `
  -Body '{"windowed":true,"res_x":1280,"res_y":720}'

Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8010/api/carla/run `
  -ContentType "application/json" `
  -Body '{"town":"Town03","duration_seconds":10,"traffic_vehicles":10,"traffic_walkers":0}'
```

Expected artifacts:

```text
outputs/carla/<run_uid>/trajectory.json
backend/static/carla/<run_uid>/camera.jpg
```

Expected database row:

```sql
SELECT run_uid, status, metrics_json
FROM simulation_runs
ORDER BY id DESC
LIMIT 1;
```

## Git And Large Files

Committed to git:

- backend/frontend source,
- install/check scripts,
- database schema code,
- docs and README.

Not committed:

- CARLA binaries,
- CARLA zip downloads,
- generated screenshots,
- trajectories,
- model checkpoints,
- datasets.

## Current Verification Status

Development-machine verification:

- `python -m pytest -q`: passed
- `npm --prefix frontend run build`: passed
- MySQL schema upgraded and CARLA seed scenarios created
- CARLA APIs return clear errors when CARLA is not installed

Full visual CARLA run requires completing the large local CARLA download first.
