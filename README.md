# Short Factory

AI YouTube Shorts production pipeline for relationship psychology content.

## Architecture

```
Research → Scripts → Scene Planning → Voice/Visuals → Render → Publish → Analytics
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for local development without Docker)
- FFmpeg (included in Docker image)

### Setup

```bash
cp .env.example .env
# Edit .env with your API keys (optional for dev — mock data used when missing)

docker compose up -d postgres redis minio
docker compose run --rm api alembic upgrade head
docker compose up -d
```

API: http://localhost:8000  
Admin UI: http://localhost:8000/admin  
MinIO Console: http://localhost:9001 (minioadmin/minioadmin)

### Admin UI

The operator dashboard at `/admin` is a server-rendered HTMX + Jinja2 UI (no separate frontend build).

| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/admin` | KPIs, recent jobs, pipeline quick actions |
| Jobs | `/admin/jobs` | Async job list with filters; detail pages auto-poll every 2s while running |
| Topics | `/admin/topics` | Research output with virality scores |
| Scripts | `/admin/scripts` | Review queue with manual approve/reject override |
| Scene Plans | `/admin/scene-plans` | Scene breakdown with audio/video asset previews |
| Videos | `/admin/videos` | HTML5 player and MP4 download |
| Publications | `/admin/publications` | Publish status with YouTube links when live |
| Analytics | `/admin/analytics` | Performance summary and rankings |

**Media preview/download** (browser-safe, no MinIO presigned URLs):

- `GET /media/asset/{id}` — stream asset for `<audio>` / `<video>` tags
- `GET /media/asset/{id}/download` — download asset
- `GET /media/video/{id}` — stream final MP4 for player
- `GET /media/video/{id}/download` — download final MP4

### Local Development (without Docker for API)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Start infra only
docker compose up -d postgres redis minio

export DATABASE_URL=postgresql+psycopg://short_factory:short_factory@localhost:5432/short_factory
export REDIS_URL=redis://localhost:6379/0
export S3_ENDPOINT_URL=http://localhost:9000

alembic upgrade head
uvicorn short_factory.api.main:app --reload

# In separate terminals:
celery -A short_factory.workers.celery_app worker --loglevel=info -Q default,research,generation,render,publish
celery -A short_factory.workers.celery_app beat --loglevel=info
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/jobs/research/run` | Trigger topic research |
| POST | `/jobs/scripts/run` | Generate scripts for top topics |
| POST | `/jobs/pipeline/run` | Run full end-to-end pipeline |
| GET | `/topics` | List ranked topics |
| POST | `/scripts/generate?topic_id=` | Generate script for topic |
| GET | `/scripts` | List scripts |
| POST | `/scripts/{id}/media` | Generate voice/visual assets |
| POST | `/scene-plans/{id}/render` | Render video |
| GET | `/videos/{id}` | Get video with preview URL |
| POST | `/videos/{id}/publish` | Publish to platform |
| GET | `/analytics/summary` | Performance dashboard data |
| POST | `/analytics/optimize` | Run feedback loop |

## Environment Variables

See [`.env.example`](.env.example) for all configuration options.

**Required for production:**
- `DATABASE_URL`, `REDIS_URL`, S3 credentials
- At least one LLM key (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `GROK_API_KEY` with `LLM_PROVIDER=grok`)
- `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` for live research
- `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, and `YOUTUBE_REFRESH_TOKEN` for publishing

### YouTube OAuth setup

1. Create OAuth 2.0 credentials in Google Cloud Console (YouTube Data API v3 enabled).
2. Set `YOUTUBE_CLIENT_ID` and `YOUTUBE_CLIENT_SECRET` in `.env`.
3. Run a one-time OAuth flow to obtain a refresh token and set `YOUTUBE_REFRESH_TOKEN`.

### Backup

```bash
./scripts/backup.sh
```

### Verify Docker Compose

```bash
./scripts/verify-docker-compose.sh
```

**Development:** Without API keys, the system uses mock Reddit/YouTube data, placeholder TTS audio, and FFmpeg-generated visual placeholders.

## Deployment (Hetzner)

```bash
export DEPLOY_HOST=your-server
export DEPLOY_DIR=/opt/short-factory
./scripts/deploy-hetzner.sh
```

## Testing

```bash
pytest
```

## Project Structure

```
src/short_factory/
├── api/          FastAPI routes + admin UI
├── research/     Topic scrapers, scoring, classification
├── scripts/      LLM script generation + validation
├── media/        Scene planning, TTS, visuals, subtitles
├── render/       FFmpeg video assembly + QA
├── publish/      Platform upload adapters
├── analytics/    Metrics collection + optimization loop
├── workers/      Celery tasks + scheduling
└── shared/       LLM client, storage, job tracking
```
