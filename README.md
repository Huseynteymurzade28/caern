# CAERN — AI-Powered Satellite & Drone Image Change Detection Platform

CAERN is a full-stack geospatial platform that detects and classifies land-use changes between two satellite or drone images. Upload a before/after image pair, run an analysis, and get an interactive map with annotated change regions, metrics, and downloadable reports — all in a dark-themed web UI.

---

## What it does

- **Change detection**: Compares two geo-referenced images (GeoTIFF or JPEG/PNG) using a classical NDI-based pipeline or YOLOv8 + SAM object detection
- **Auto-categorization**: Each detected region is classified into one of four categories — `NEW_STRUCTURE`, `DEMOLITION`, `VEGETATION`, `SURFACE_CHANGE`
- **Interactive map**: Results rendered on a Leaflet map with per-category layer toggles, opacity control, and clickable popups
- **Metrics dashboard**: Total changed area (m²), change percentage, confidence score, per-category breakdown (bar chart + donut gauge)
- **Reports**: Export results as CSV or PDF (cover page, summary, metric table, embedded map screenshot, object list, methodology section)
- **Real-time progress**: Analysis progress streamed to the browser via Server-Sent Events (SSE)
- **JWT auth + RBAC**: Login/refresh token flow with role-based access control

---

## Architecture

```
Browser (React + Leaflet)
        │  HTTPS
        ▼
    nginx (TLS termination, reverse proxy)
        │                │
        ▼                ▼
  FastAPI (API)    React SPA (static)
        │
   ┌────┴────┐
   │         │
Redis     Postgres (PostGIS)
   │
Celery Worker
   │
 MinIO (image storage)
```

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Leaflet.js, Recharts, Zustand, React Query |
| Backend API | Python 3.11, FastAPI, Uvicorn (4 workers) |
| Task Queue | Celery 5 + Redis 7 |
| Database | PostgreSQL 15 + PostGIS 3.4, SQLAlchemy async, Alembic |
| Object Storage | MinIO |
| AI / CV | YOLOv8 (Ultralytics), Segment Anything Model (SAM), OpenCV, Rasterio, GDAL |
| Reporting | WeasyPrint, ReportLab, Jinja2 |
| Infrastructure | Docker Compose, nginx (self-signed TLS for local dev) |

---

## Prerequisites

| Requirement | Version |
|---|---|
| Docker | 24+ |
| Docker Compose | v2 (included in Docker Desktop) |
| `make` | any |
| `openssl` | any (for TLS cert generation) |

> **GPU (optional):** If you have an NVIDIA GPU, install `nvidia-container-toolkit` and uncomment the `deploy.resources` block in `docker-compose.yml` under the `worker` service. The pipeline falls back to CPU automatically when no GPU is detected.

---

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd caern
```

### 2. Copy environment variables

```bash
cp .env.example .env
```

Open `.env` and change the values below before running anything:

```env
# Must be changed in production
JWT_SECRET_KEY=<long-random-string>

POSTGRES_PASSWORD=<your-db-password>
MINIO_ROOT_PASSWORD=<your-minio-password>
```

All other defaults work for local development as-is.

### 3. Start all services

```bash
sudo make up
```

This command:
1. Generates a self-signed TLS certificate under `nginx/certs/` (if missing)
2. Builds Docker images for the API, Celery worker, and React frontend
3. Starts all containers (nginx, api, worker, redis, postgres, minio, frontend)

> The first build downloads PyTorch, GDAL, and model weights — expect **5–15 minutes** depending on your internet speed.

### 4. Run database migrations

```bash
sudo make migrate
```

Applies all Alembic migrations against the running Postgres container.

### 5. Seed the admin user

```bash
sudo make seed
```

Creates the initial admin account:

| Field | Value |
|---|---|
| Email | `admin@caern.local` |
| Password | `caern2024!` |

### 6. Open the app

Navigate to **[https://localhost](https://localhost)** in your browser.

> Because the TLS certificate is self-signed, you will see a browser warning. Click **Advanced → Proceed to localhost** (Chrome) or **Accept the Risk** (Firefox). This is expected for local development.

---

## Environment variables reference

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_USER` | `caern` | Database user |
| `POSTGRES_PASSWORD` | `caern_secret` | Database password |
| `POSTGRES_DB` | `caern_db` | Database name |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `MINIO_ROOT_USER` | `caern_minio` | MinIO admin user |
| `MINIO_ROOT_PASSWORD` | `caern_minio_secret` | MinIO admin password |
| `MINIO_BUCKET` | `caern-images` | Bucket for uploaded images |
| `JWT_SECRET_KEY` | *(change me)* | Secret used to sign JWTs |
| `JWT_ACCESS_TOKEN_EXPIRE_HOURS` | `8` | Access token lifetime |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `YOLO_MODEL_PATH` | `/app/models/yolov8n.pt` | Path to YOLOv8 weights inside the container |
| `SAM_MODEL_PATH` | `/app/models/sam_vit_h.pth` | Path to SAM weights inside the container |
| `MODEL_CONFIDENCE_THRESHOLD` | `0.5` | Minimum confidence for a detection to be kept |
| `MAX_UPLOAD_SIZE_MB` | `500` | Maximum upload size per image |
| `CORS_ORIGINS` | `http://localhost:3000,https://caern.local` | Comma-separated list of allowed CORS origins |
| `APP_ENV` | `development` | `development` or `production` |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Make targets

| Command | Description |
|---|---|
| `sudo make up` | Build images and start all services |
| `sudo make down` | Stop all containers (volumes preserved) |
| `sudo make reset` | Stop all containers **and delete volumes** (full wipe) |
| `sudo make build` | Rebuild images without starting (use after adding a dependency) |
| `sudo make migrate` | Run Alembic migrations |
| `sudo make seed` | Create the default admin user |
| `sudo make test` | Run the backend test suite with pytest |
| `sudo make certs` | Regenerate the self-signed TLS certificate |

---

## Running analysis

1. Log in at `https://localhost`
2. Click **New Analysis** in the sidebar
3. Upload a **before** image and an **after** image (GeoTIFF recommended for accurate area calculations; JPEG/PNG also supported)
4. Configure parameters:
   - **Confidence threshold** (50–95%) — higher values produce fewer but more reliable detections
   - **Minimum area** (25–500 m²) — regions smaller than this are ignored
   - **Detection mode** — `classical` (fast, CPU-only) or `yolov8+sam` (accurate, GPU-recommended)
5. Click **Run Analysis**. Progress is shown in real time (Upload → Preprocess → Detect → Classify → Finalize)
6. When complete, the map zooms to the result area. Use the layer panel on the right to toggle categories and adjust opacity
7. Download a report with the **Export CSV** or **Export PDF** button

---

## API documentation

Interactive API docs are available while the stack is running:

- **Swagger UI**: `https://localhost/docs`
- **ReDoc**: `https://localhost/redoc`

### Key endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/auth/login` | Obtain access + refresh tokens |
| `POST` | `/api/auth/refresh` | Refresh access token |
| `POST` | `/api/images/upload` | Upload a before/after image pair |
| `POST` | `/api/jobs` | Create and queue a new analysis job |
| `GET` | `/api/jobs` | List all jobs |
| `GET` | `/api/jobs/{id}` | Get job details and status |
| `GET` | `/api/jobs/{id}/metrics` | Get computed metrics for a completed job |
| `GET` | `/api/jobs/{id}/progress?token=...` | SSE stream for real-time progress |
| `GET` | `/api/reports/jobs/{id}/download.csv` | Download results as CSV |
| `GET` | `/api/reports/jobs/{id}/download.pdf` | Download results as PDF |
| `GET` | `/health` | Health check |

---

## Project structure

```
caern/
├── backend/
│   ├── ai_models/          # YOLOv8 and SAM model wrappers
│   ├── alembic/            # Database migrations
│   ├── analysis_engine/    # Celery app, job orchestrator, classical detector
│   ├── api/                # FastAPI routers and dependency injection
│   ├── auth/               # JWT handling, password hashing, RBAC
│   ├── common_utils/       # Config (pydantic-settings), logging, exceptions
│   ├── data_access/        # SQLAlchemy async session and base model
│   ├── geo_processing/     # GDAL/Rasterio image alignment and metadata
│   ├── models/             # AI model weight files (yolov8n.pt, sam_vit_h.pth)
│   ├── notification/       # SSE broadcaster, SMTP email
│   ├── reporting/          # CSV and PDF report generators
│   ├── storage/            # MinIO client
│   ├── tests/              # Pytest test suite
│   ├── main.py             # FastAPI app factory
│   ├── seed.py             # Admin user seeder
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/     # MapView, LayerManager, MetricsPanel, NewAnalysis, ...
│   │   └── index.css
│   ├── package.json
│   └── vite.config.ts
├── nginx/
│   ├── nginx.conf
│   └── certs/              # Auto-generated TLS certificate
├── docker-compose.yml
├── Makefile
└── .env.example
```

---

## Detection pipeline

```
Upload (MinIO)
      │
  Geo alignment (Rasterio — reproject, clip, resample to same grid)
      │
  Change mask (NDI thresholding + morphological cleanup)
      │
  Connected-component labeling (scipy.ndimage)
      │
  [Optional] YOLOv8 object detection → SAM segmentation refinement
      │
  Auto-categorization (RGB channel analysis per region)
      │
  Metric computation (area m², centroid, bbox, confidence, histogram)
      │
  Persist to PostGIS → stream progress via SSE → ready
```

---

## Development tips

**Rebuild after adding a Python dependency:**

```bash
# Add the package to backend/requirements.txt, then:
sudo docker compose build api worker
sudo make up
```

**Rebuild after adding an npm package:**

```bash
# Add the package to frontend/package.json, then:
sudo docker compose build frontend
sudo make up
```

**Tail worker logs (useful for debugging analysis jobs):**

```bash
sudo docker compose logs worker -f --tail=100
```

**Connect to Postgres directly:**

```bash
sudo docker compose exec postgres psql -U caern -d caern_db
```

**Access MinIO console:**

Open `http://localhost:9001` in your browser (credentials from `.env`: `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`).

**Run tests:**

```bash
sudo make test
# or with coverage:
sudo docker compose exec api pytest --cov=. --cov-report=term-missing
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Browser shows "502 Bad Gateway" after a rebuild | `sudo docker compose restart nginx` |
| `make seed` fails with import error | Ensure migrations ran first: `sudo make migrate` |
| Analysis stuck at 30% | Check worker logs: `sudo docker compose logs worker --tail=50`. Usually means model weights are missing from `backend/models/` |
| CORS error in browser console | Add your origin to `CORS_ORIGINS` in `.env`, then restart the api: `sudo docker compose restart api` |
| Self-signed cert warning | Expected — click "Advanced → Proceed" in Chrome or "Accept the Risk" in Firefox |

---

## License

MIT
