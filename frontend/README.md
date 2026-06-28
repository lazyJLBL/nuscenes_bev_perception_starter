# AutoDrive OS Frontend

Vue 3 + Vite frontend for the nuScenes-first offline model comparison platform.
The default route opens the AD Sandbox workspace directly; the old module view is kept only under `/dev/modules/preprocessing` for development checks.

By default the Vite dev server runs on `http://127.0.0.1:5174` and proxies `/api` and `/static` to the backend at `http://127.0.0.1:8010`.

## Run Locally

From the repository root:

```bash
python -m backend.main
npm install --prefix frontend
npm run dev
```

Or from this directory:

```bash
npm install
npm run dev
```

To point the proxy at another backend port:

```bash
VITE_BACKEND_URL=http://127.0.0.1:8010 npm run dev
```

## Main Routes

- `/` opens the offline experiment sandbox.
- `/experiments` shows recent run records from `outputs/experiments/*/run_record.json`.
- `/system` shows backend health and runtime capabilities.
- `/dev/modules/preprocessing` keeps the legacy module selector view for development checks.

## Build Check

```bash
npm run build
```
