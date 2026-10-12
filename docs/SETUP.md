# Setup and operation

Prerequisites: Python **3.12**, Node.js **22 or later**, npm, and Git. Docker Compose is optional.
Use a separate virtual environment for each project. Python 3.14 is not the tested runtime.

## Docker (one command)

From the repository root:

```sh
docker compose up --build
```

Open http://localhost:8080. API documentation is at http://localhost:8000/docs.
The backend health check controls frontend startup. Named volumes persist the database and model artifacts.
Stop with `docker compose down`; the volume remains. To run both projects concurrently,
change one project's host ports to `8001:8000` and `8081:8080` in `compose.yaml`.
UI API calls go through the frontend proxy, so no frontend code change is needed.

## Native Windows / PowerShell

Terminal 1, from the repository root:

```powershell
cd backend
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If `py -3.12` is unavailable, install Python 3.12 or use its full executable path.
No PowerShell activation script is necessary.

Terminal 2, from the repository root:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open the URL printed by Vite (normally http://localhost:5173).

## macOS / Linux

Terminal 1:

```sh
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```sh
cd frontend
npm ci
npm run dev
```

## Checks

From `backend`, with the virtual environment active, run `python -m pytest -q`.
On Windows use `.venv\Scripts\python.exe -m pytest -q`.
From `frontend`, run `npm run build` (`npm.cmd run build` on Windows).

## Configuration

`.env.example` lists demo configuration. Docker Compose reads a root `.env` when present.
Native Python does **not** automatically read `.env`; set variables in the shell before starting.
Do not put API credentials in frontend build variables; frontend source is public.
These known demo tokens are intended only for local synthetic examples.

## Troubleshooting

- UI network errors: start the API on port 8000; check `/health`; inspect API terminal output.
- Unauthorized: restore the documented demo token or match UI input to your backend environment variable.
- Port in use: stop the other project before starting; each repository uses the same default ports.
- Native custom API port: set `API_PROXY_TARGET` before starting Vite (PowerShell: `$env:API_PROXY_TARGET="http://127.0.0.1:8001"`).
- npm cache permission errors: `npm.cmd ci --cache ./npm-cache` uses a local cache; add `npm-cache/` to your local ignore rules.
- Docker builds need internet on first run. They are defined and included in CI; local validation does not assume a Docker daemon exists.




## Production build preview (also works in restricted Windows sandboxes)

With the backend running, from `frontend`:

```sh
npm ci
npm run build
npm run preview
```

Open the URL printed by Vite (normally http://localhost:4173). On Windows use `npm.cmd`.
Preview uses the same `/api` proxy as development. This was the browser-verified native
path. Development dependency prebundling can fail inside restricted Windows sandboxes
because esbuild scans parent directories; production build and preview avoid that scan.
On a regular terminal `npm run dev` remains the development command.

`backend/constraints.txt` pins the resolved versions used during validation. It constrains
dependencies from `requirements.txt` without requiring every listed package to be installed.
`frontend/package-lock.json` fixes frontend dependencies for `npm ci`.
