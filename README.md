# nuScenes BEV Perception Sandbox Platform

This repository is now a productized autonomous-driving experiment sandbox. The current pushed version is **Batch 1: MySQL-backed admin and client run management**.

The platform still uses the existing nuScenes offline perception/decision/planning workflow for simulation results. CARLA integration will be delivered in later batches.

## Current Capabilities

- FastAPI backend for health checks, module metadata, offline experiment execution, inference previews, and product APIs.
- Vue 3 frontend with:
  - client sandbox page,
  - client experiment history page,
  - admin console for models and simulation scenarios,
  - system status page.
- MySQL 8.0 persistence for:
  - users,
  - model catalog,
  - simulation scenario templates,
  - simulation runs,
  - run artifacts.
- Backward-compatible filesystem outputs under `outputs/`.
- Existing nuScenes offline experiment records remain readable from `outputs/experiments/*/run_record.json`.

## Repository Layout

```text
backend/
  api/routes.py              Existing nuScenes and inference API
  api/product_routes.py      MySQL-backed admin/client API
  db.py                      SQLAlchemy models, seed data, persistence helpers
configs/                     Dataset, model, and path configuration
docs/database_design.md      MySQL schema design
frontend/
  src/views/AdminView.vue    Admin console
  src/views/ExperimentsView.vue
  src/views/SandboxView.vue
scripts/                     nuScenes setup, training, inference, validation scripts
src/                         BEV, detection, geometry, experiment logic
tests/                       API and core behavior tests
```

Generated files are ignored by git: `outputs/`, `backend/static/`, model checkpoints, datasets, and local build artifacts.

## Requirements

- Windows 10/11 or Linux
- Python 3.8+
- Node.js 18+
- MySQL 8.0
- PyTorch installed for your CUDA or CPU environment
- nuScenes mini dataset if you want to run the existing offline perception pipeline

Install project dependencies:

```bash
pip install -r requirements.txt
npm install --prefix frontend
```

## MySQL Setup

Create the database:

```sql
CREATE DATABASE IF NOT EXISTS nuscenes_bev_platform
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

Set the backend connection string before starting the API:

```powershell
$env:DATABASE_URL="mysql+pymysql://root:0000@localhost:3306/nuscenes_bev_platform?charset=utf8mb4"
```

Do not commit real passwords. `.env.example` contains only a template.

Initialize schema and seed data:

```powershell
python - <<'PY'
from backend.db import create_schema
create_schema(seed=True)
print("database ready")
PY
```

Seed data includes:

- `admin` user,
- `client_demo` user,
- model catalog entries from the current experiment registry,
- one nuScenes offline scenario,
- one disabled Unity placeholder from the previous planning stage.

## Run The Platform

Terminal 1:

```powershell
$env:DATABASE_URL="mysql+pymysql://root:0000@localhost:3306/nuscenes_bev_platform?charset=utf8mb4"
python -m backend.main
```

Terminal 2:

```powershell
npm run dev
```

Open:

- frontend: `http://127.0.0.1:5174`
- admin console: `http://127.0.0.1:5174/admin`
- backend status: `http://127.0.0.1:8010/api/health`
- database status: `http://127.0.0.1:8010/api/db/status`

## Main API Endpoints

Existing nuScenes/offline API:

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

## Admin Workflow

1. Open `/admin`.
2. Check the MySQL status badge.
3. Use "Initialize" if the database has not been prepared.
4. Add or edit models in the model catalog.
5. Add or edit simulation scenario templates.

Model files, checkpoints, images, and large artifacts are stored by URI/path. They are not stored as database blobs.

## Client Workflow

1. Open `/`.
2. Run the current nuScenes offline sandbox.
3. Open `/experiments`.
4. The page first reads MySQL client runs. If MySQL is unavailable, it falls back to local JSON records.

## Validation

Run backend tests:

```bash
python -m pytest -q
```

Build frontend:

```bash
npm --prefix frontend run build
```

Check MySQL seed data:

```sql
SELECT COUNT(*) FROM app_users;
SELECT COUNT(*) FROM model_catalog;
SELECT COUNT(*) FROM simulation_scenarios;
SELECT COUNT(*) FROM simulation_runs;
```

Batch 1 verification on the development machine:

- `python -m pytest -q`: passed
- `npm --prefix frontend run build`: passed
- MySQL schema initialized and seed data readable

## Next Batch

Batch 2 will add CARLA 0.9.15 Windows installer and environment-check scripts. CARLA binaries will be downloaded to `D:\CARLA` and will not be committed to git.
