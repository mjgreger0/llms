# LLM Serve Dashboard

Centralized control plane for LLM cluster management. This FastAPI application provides APIs for managing machines, models, container configurations, and monitoring cluster health.

## Requirements

- Python 3.11+
- PostgreSQL 15+ with TimescaleDB extension
- Required Python packages (see `pyproject.toml`)

## Quick Start

### 1. Set Environment Variables

Create a `.env` file or export the following environment variables:

```bash
# Required
export LLM_SERVE_ENCRYPTION_KEY="your-secret-key-here-minimum-32-characters"

# Database (adjust for your setup)
export DATABASE_URL="postgresql+asyncpg://llmserve:llmserve@localhost:5432/llmserve"
```

### 2. Install Dependencies

```bash
cd dashboard
pip install -e .
# Or with dev dependencies:
pip install -e ".[dev]"
```

### 3. Initialize Database

```bash
python -m dashboard.backend.scripts.init_db
```

This will:
- Create the database if it doesn't exist
- Run all Alembic migrations
- Seed initial settings

### 4. Run the Application

```bash
uvicorn dashboard.backend.main:app --host 0.0.0.0 --port 8080 --reload
```

The API will be available at `http://localhost:8080`.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_SERVE_ENCRYPTION_KEY` | Yes | - | Encryption key for credentials (min 32 chars) |
| `DATABASE_URL` | No | `postgresql+asyncpg://llmserve:llmserve@localhost:5432/llmserve` | PostgreSQL connection URL |
| `DATABASE_POOL_SIZE` | No | `20` | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | No | `10` | Max overflow connections |
| `HOST` | No | `0.0.0.0` | Server bind host |
| `PORT` | No | `8080` | Server bind port |
| `ALLOWED_NETWORKS` | No | `192.168.0.0/24` | Allowed CORS origins (comma-separated) |
| `MODEL_PATH` | No | `/data/projects/ai/models` | Model storage path |
| `METRICS_RETENTION_DAYS` | No | `30` | TimescaleDB metrics retention |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | No | `json` | Log format (json or console) |

## API Endpoints

### Health Check

```bash
# Check system health
curl http://localhost:8080/health
```

Response:
```json
{
  "status": "healthy",
  "database_connected": true,
  "version": "0.1.0"
}
```

### Cluster Status

```bash
# Get cluster overview
curl http://localhost:8080/api/cluster/status
```

Response:
```json
{
  "total_machines": 0,
  "online_machines": 0,
  "total_gpus": 0,
  "free_gpus": 0,
  "running_models": []
}
```

### Machines

```bash
# List all machines
curl http://localhost:8080/api/machines

# Get specific machine
curl http://localhost:8080/api/machines/{machine_id}
```

### Models

```bash
# List all models with quantizations
curl http://localhost:8080/api/models
```

### Container Configurations

```bash
# List all container configs
curl http://localhost:8080/api/containers

# Get specific config
curl http://localhost:8080/api/containers/{config_id}
```

### Settings

```bash
# Get all settings
curl http://localhost:8080/api/settings

# Get specific setting
curl http://localhost:8080/api/settings/{key}

# Update setting
curl -X PUT http://localhost:8080/api/settings/{key} \
  -H "Content-Type: application/json" \
  -d '{"value": "new_value"}'
```

### Logs

```bash
# Get recent logs (with optional filters)
curl "http://localhost:8080/api/logs?level=INFO&limit=100"
```

## Database Migrations

### Run Migrations

```bash
cd dashboard/backend/db/migrations
alembic upgrade head
```

### Rollback Migration

```bash
alembic downgrade -1
```

### Create New Migration

```bash
alembic revision --autogenerate -m "Description of changes"
```

## Project Structure

```
dashboard/
├── pyproject.toml           # Project configuration
├── README.md                # This file
└── backend/
    ├── __init__.py
    ├── main.py              # FastAPI application entry point
    ├── config.py            # Configuration management
    ├── logging_config.py    # Structured logging setup
    ├── middleware.py        # Request middleware
    ├── api/
    │   ├── __init__.py
    │   ├── health.py        # Health check endpoint
    │   └── control.py       # Control API endpoints
    ├── db/
    │   ├── __init__.py
    │   ├── base.py          # SQLAlchemy base and mixins
    │   ├── session.py       # Database session management
    │   └── migrations/
    │       ├── alembic.ini
    │       ├── env.py
    │       └── versions/
    │           ├── 001_initial_tables.py
    │           └── 002_timescaledb_hypertables.py
    ├── models/
    │   ├── __init__.py
    │   ├── database.py      # SQLAlchemy models
    │   └── schemas.py       # Pydantic schemas
    ├── services/
    │   ├── __init__.py
    │   ├── cluster_state.py # Cluster state management
    │   ├── machine_service.py
    │   ├── model_service.py
    │   ├── container_service.py
    │   └── settings_service.py
    └── scripts/
        ├── __init__.py
        └── init_db.py       # Database initialization
```

## Database Schema

### Regular Tables
- `machines` - Registered GPU servers
- `models` - Base LLM models
- `model_quantizations` - Model quantization variants
- `container_configs` - Container runtime configurations
- `credentials` - Encrypted credential storage
- `settings` - Key-value settings storage

### TimescaleDB Hypertables
- `cpu_stats` - CPU metrics time-series
- `gpu_stats` - GPU metrics time-series
- `memory_stats` - Memory metrics time-series

## Troubleshooting

### Database Connection Failed

1. Verify PostgreSQL is running:
   ```bash
   pg_isready -h localhost -p 5432
   ```

2. Check TimescaleDB extension is installed:
   ```sql
   SELECT * FROM pg_extension WHERE extname = 'timescaledb';
   ```

3. Verify connection URL in environment:
   ```bash
   echo $DATABASE_URL
   ```

### Encryption Key Error

The `LLM_SERVE_ENCRYPTION_KEY` must be at least 32 characters:
```bash
export LLM_SERVE_ENCRYPTION_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
```

### Migration Errors

1. Ensure database exists:
   ```bash
   createdb llmserve
   ```

2. Check current migration state:
   ```bash
   cd dashboard/backend/db/migrations
   alembic current
   ```

3. View migration history:
   ```bash
   alembic history
   ```

### TimescaleDB Hypertable Issues

If hypertable creation fails, ensure TimescaleDB is enabled:
```sql
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
```

### Logs Not Appearing

Check `LOG_LEVEL` environment variable. Set to `DEBUG` for verbose output:
```bash
export LOG_LEVEL=DEBUG
```

## API Documentation

When the server is running, OpenAPI documentation is available at:
- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`
- OpenAPI JSON: `http://localhost:8080/openapi.json`

## Development

### Run with Auto-reload

```bash
uvicorn dashboard.backend.main:app --reload --log-level debug
```

### Type Checking

```bash
mypy dashboard/backend
```

### Linting

```bash
ruff check dashboard/backend
```

### Testing

```bash
pytest dashboard/backend/tests
```
