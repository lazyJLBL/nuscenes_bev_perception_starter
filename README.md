# CARLA BEV Perception Sandbox Platform

Current version: **Batch 2: CARLA 0.9.15 installer and environment checks**.

This project is becoming a CARLA-based autonomous-driving simulation sandbox. Batch 1 added the MySQL-backed admin/client platform. Batch 2 adds local CARLA download, installation, and environment validation tools. CARLA backend execution will be implemented in Batch 3.

## What Works Now

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
- Existing nuScenes offline experiment flow remains available.
- CARLA 0.9.15 installer script for Windows.
- CARLA environment checker for:
  - installation path,
  - `CarlaUE4.exe`,
  - disk space,
  - ports 2000/2001,
  - GPU info,
  - Python API importability.

## Why CARLA 0.9.15

The development machine is Windows 10 with an RTX 4070 Laptop GPU and 32GB RAM. CARLA 0.9.15 is the selected packaged Windows release for this environment. The installer uses the official CARLA tiny URLs from the 0.9.15 release note:

- `https://tiny.carla.org/carla-0-9-15-windows`
- `https://tiny.carla.org/additional-maps-0-9-15-windows`

The downloads resolve to CARLA's release CDN. The binaries are not committed to git.

## Repository Layout

```text
backend/
  api/routes.py              Existing nuScenes and inference API
  api/product_routes.py      MySQL-backed admin/client API
  db.py                      SQLAlchemy models and seed data
configs/                     Dataset, model, and path configuration
docs/database_design.md      MySQL schema design
frontend/
  src/views/AdminView.vue    Admin console
  src/views/ExperimentsView.vue
  src/views/SandboxView.vue
scripts/
  install_carla_0915.ps1     CARLA 0.9.15 Windows installer
  check_carla_environment.py CARLA local environment checker
src/                         BEV, detection, geometry, experiment logic
tests/                       API and core behavior tests
```

Ignored large/generated paths include `outputs/`, `backend/static/`, model checkpoints, datasets, CARLA downloads, and local CARLA install directories.

## Requirements

- Windows 10/11
- Python 3.8+
- Node.js 18+
- MySQL 8.0
- PowerShell
- At least 55GB free disk space on the CARLA install drive if Additional Maps are installed
- PyTorch for the existing nuScenes workflow

Install project dependencies:

```bash
pip install -r requirements.txt
npm install --prefix frontend
```

## MySQL Setup

Create database:

```sql
CREATE DATABASE IF NOT EXISTS nuscenes_bev_platform
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

Set the connection string:

```powershell
$env:DATABASE_URL="mysql+pymysql://root:0000@localhost:3306/nuscenes_bev_platform?charset=utf8mb4"
```

Initialize schema:

```powershell
python - <<'PY'
from backend.db import create_schema
create_schema(seed=True)
print("database ready")
PY
```

## Install CARLA 0.9.15

Default install location:

```text
D:\CARLA\CARLA_0.9.15
```

Run the installer:

```powershell
.\scripts\install_carla_0915.ps1
```

Install only the base simulator and skip Additional Maps:

```powershell
.\scripts\install_carla_0915.ps1 -SkipAdditionalMaps
```

Use a different root directory:

```powershell
.\scripts\install_carla_0915.ps1 -InstallRoot "E:\Simulators\CARLA"
```

The script downloads:

```text
D:\CARLA\downloads\CARLA_0.9.15.zip
D:\CARLA\downloads\AdditionalMaps_0.9.15.zip
```

Then extracts into:

```text
D:\CARLA\CARLA_0.9.15
```

## Check CARLA Environment

Set environment variables:

```powershell
$env:CARLA_HOME="D:\CARLA\CARLA_0.9.15"
$env:CARLA_HOST="127.0.0.1"
$env:CARLA_PORT="2000"
```

Run:

```powershell
python scripts/check_carla_environment.py
```

Expected report fields:

- `carla_home_exists`
- `carla_executable_exists`
- `ports.2000`
- `ports.2001`
- `gpu`
- `python_api.available`

If CARLA is not installed yet, the checker exits with code `2` and prints a readable JSON report.

## Start Current Platform

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

## Current APIs

Existing API:

```text
GET  /api/health
GET  /api/modules
GET  /api/experiments
GET  /api/experiments/latest
POST /api/run_experiment
POST /api/run_sandbox
POST /api/inference/{model_id}
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

CARLA runtime API will be added in Batch 3.

## Validation

Run:

```bash
python -m pytest -q
npm --prefix frontend run build
python scripts/check_carla_environment.py
```

Batch 2 verification on the development machine:

- Unit/API tests: passed
- Frontend build: passed
- CARLA release URLs: reachable through official tiny CARLA links
- Environment checker: reports missing CARLA cleanly if install has not been run

## Next Batch

Batch 3 will add the FastAPI CARLA service:

- `GET /api/carla/status`
- `POST /api/carla/start`
- `POST /api/carla/stop`
- `GET /api/carla/maps`
- `POST /api/carla/run`

It will also write CARLA run artifacts and metrics into MySQL.
