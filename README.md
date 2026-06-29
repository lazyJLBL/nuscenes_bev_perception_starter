# CARLA BEV Perception Sandbox Platform

Current version: **Batch 3: CARLA backend simulation runner**.

The platform now has a FastAPI CARLA service layer. It can inspect a local CARLA 0.9.15 installation, start/stop the simulator, list maps, run a basic visual simulation, export trajectory and camera artifacts, and persist CARLA run metadata to MySQL.

## Current Capabilities

- MySQL-backed platform data:
  - users,
  - model catalog,
  - simulation scenarios,
  - simulation runs,
  - run artifacts.
- Vue frontend:
  - client sandbox,
  - client experiment history,
  - admin model/scenario console,
  - system status.
- Existing nuScenes offline workflow remains available.
- CARLA 0.9.15 installer and environment checker.
- CARLA backend API:
  - status,
  - start,
  - stop,
  - maps,
  - run.
- CARLA run outputs:
  - `outputs/carla/<run_uid>/trajectory.json`,
  - `backend/static/carla/<run_uid>/camera.jpg`,
  - MySQL `simulation_runs` and `simulation_run_artifacts` records when `DATABASE_URL` is configured.

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

The script uses official CARLA tiny URLs:

```text
https://tiny.carla.org/carla-0-9-15-windows
https://tiny.carla.org/additional-maps-0-9-15-windows
```

CARLA binaries are installed outside the repository under `D:\CARLA` and are not committed.

## Check CARLA Environment

```powershell
python scripts/check_carla_environment.py
```

The checker reports:

- install path,
- executable path,
- free disk space,
- port 2000/2001 status,
- GPU adapters,
- Python API import status.

If CARLA is not installed, the checker exits with a non-zero code and prints a JSON report instead of crashing.

## Start The Platform

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
- admin: `http://127.0.0.1:5174/admin`
- backend health: `http://127.0.0.1:8010/api/health`
- database status: `http://127.0.0.1:8010/api/db/status`
- CARLA status: `http://127.0.0.1:8010/api/carla/status`

## CARLA API

```text
GET  /api/carla/status
POST /api/carla/start
POST /api/carla/stop
GET  /api/carla/maps
POST /api/carla/run
```

Start CARLA visible window:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8010/api/carla/start `
  -ContentType "application/json" `
  -Body '{"windowed":true,"res_x":1280,"res_y":720}'
```

Run a 10-second Town03 demo:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8010/api/carla/run `
  -ContentType "application/json" `
  -Body '{"town":"Town03","duration_seconds":10,"traffic_vehicles":10,"traffic_walkers":0}'
```

Example run result fields:

```text
run_uid
town
metrics.distance_m
metrics.collision_count
metrics.average_speed_kmh
trajectory_path
camera_image_url
timesteps
stats
```

## Existing Product API

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

Smoke test CARLA status without installation:

```powershell
Invoke-RestMethod http://127.0.0.1:8010/api/carla/status
```

Expected behavior when CARLA is not installed:

- `installed=false`,
- `connected=false`,
- readable `error` message,
- no backend crash.

Batch 3 verification on the development machine:

- Unit/API tests: passed
- Frontend build: passed
- CARLA status API handles missing local CARLA cleanly

## Next Batch

Batch 4 will update the database and admin console from Unity-era scenario fields to CARLA multi-scenario management:

- `dataset_source=carla`,
- CARLA Town selection,
- weather,
- traffic vehicles,
- traffic walkers,
- duration,
- spawn point,
- synchronous mode.
