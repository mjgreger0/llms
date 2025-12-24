# Configuration Module Documentation

## Overview

The Configuration Module provides environment-based configuration and structured logging for the LLM Serve Daemon. It uses Pydantic Settings for automatic environment variable loading and validation.

## Files

- `/src/config.py` - Configuration class with validation
- `/src/logger.py` - Structured logging setup
- `/src/__init__.py` - Module exports

## Environment Variables

### Required Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `DASHBOARD_URL` | string | WebSocket URL of Dashboard control plane | `ws://dashboard.local:8080/ws/daemon` |

### Optional Variables with Defaults

| Variable | Type | Default | Description | Validation |
|----------|------|---------|-------------|------------|
| `MACHINE_ID` | string | hostname | Unique machine identifier | - |
| `PROC_PATH` | path | `/host/proc` | Path to host's /proc directory | Must be absolute |
| `SYS_PATH` | path | `/host/sys` | Path to host's /sys directory | Must be absolute |
| `PODMAN_SOCKET` | path | `/run/podman/podman.sock` | Path to Podman socket | Must be absolute |
| `MODEL_PATH` | path | `/models` | Path to model storage | Must be absolute |
| `STATS_INTERVAL_SECONDS` | int | `6` | Stats collection interval | 1-3600 |
| `HEALTH_CHECK_INTERVAL_SECONDS` | int | `5` | Health check interval | 1-300 |
| `LOG_LEVEL` | enum | `INFO` | Logging level | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `LOG_FORMAT` | enum | `json` | Log output format | json, console |

## Usage

### Basic Usage

```python
from src import config, logger

# Access configuration
print(f"Machine ID: {config.MACHINE_ID}")
print(f"Dashboard URL: {config.DASHBOARD_URL}")
print(f"Stats Interval: {config.STATS_INTERVAL_SECONDS}s")

# Use logger
logger.info("daemon_starting", machine_id=config.MACHINE_ID)
```

### Running with Environment Variables

```bash
# Set required variables
export DASHBOARD_URL="ws://dashboard.local:8080/ws/daemon"

# Optional: customize settings
export MACHINE_ID="gpu-node-001"
export LOG_LEVEL="DEBUG"
export LOG_FORMAT="console"
export STATS_INTERVAL_SECONDS="10"

# Run daemon
python -m src.main
```

### Using .env File

Create a `.env` file in the daemon directory:

```env
DASHBOARD_URL=ws://dashboard.local:8080/ws/daemon
MACHINE_ID=gpu-node-001
LOG_LEVEL=INFO
LOG_FORMAT=json
STATS_INTERVAL_SECONDS=6
HEALTH_CHECK_INTERVAL_SECONDS=5
```

The configuration will automatically load from the `.env` file.

## Validation

### Automatic Validation

The Config class automatically validates:

1. **Required Variables**: Missing `DASHBOARD_URL` raises `ValidationError`
2. **Path Variables**: All paths must be absolute (checked at initialization)
3. **Interval Ranges**: Stats interval (1-3600s), health check interval (1-300s)
4. **Enum Values**: LOG_LEVEL and LOG_FORMAT must match allowed values

### Examples

**Missing Required Variable:**
```python
# Without DASHBOARD_URL set
config = Config()
# Raises: ValidationError: Field required [type=missing, input_value={...}]
```

**Invalid Path (relative instead of absolute):**
```python
os.environ["PROC_PATH"] = "relative/path"
config = Config()
# Raises: ValidationError: PROC_PATH must be an absolute path
```

**Invalid Interval:**
```python
os.environ["STATS_INTERVAL_SECONDS"] = "-1"
config = Config()
# Raises: ValidationError: Input should be greater than or equal to 1
```

## Logging

### JSON Format (Production)

Default format for production. Outputs structured JSON logs:

```bash
export LOG_FORMAT="json"
```

Example output:
```json
{"event": "daemon_starting", "level": "INFO", "timestamp": "2025-12-23T10:30:45.123456Z", "machine_id": "gpu-node-001"}
{"event": "stats_collected", "level": "INFO", "timestamp": "2025-12-23T10:30:51.234567Z", "cpu_load": 45.2, "memory_used_gb": 32.5}
```

### Console Format (Development)

Human-readable format for development:

```bash
export LOG_FORMAT="console"
```

Example output:
```
2025-12-23 10:30:45 [info     ] daemon_starting                machine_id=gpu-node-001
2025-12-23 10:30:51 [info     ] stats_collected                cpu_load=45.2 memory_used_gb=32.5
```

### Log Levels

Available log levels (set via `LOG_LEVEL`):

```python
logger.debug("debug_message", detail="verbose debugging")
logger.info("info_message", detail="general information")
logger.warning("warning_message", detail="something unexpected")
logger.error("error_message", detail="an error occurred", error_code=500)
logger.critical("critical_message", detail="critical failure")
```

### Structured Context

Always use keyword arguments for structured logging:

```python
# Good - structured fields
logger.info("container_started",
    container_id="abc123",
    model="llama-3.1-8b",
    gpus=[0, 1])

# Avoid - unstructured message
logger.info(f"Started container {container_id} with model {model}")
```

## Auto-Generated Fields

### MACHINE_ID

If `MACHINE_ID` is not provided, it's automatically generated from the system hostname:

```python
import socket
# MACHINE_ID defaults to socket.gethostname()
```

This ensures every daemon instance has a unique identifier even without explicit configuration.

## Container Deployment

When running in a container, mount host paths and provide configuration:

```bash
podman run \
  -v /proc:/host/proc:ro \
  -v /sys:/host/sys:ro \
  -v /run/podman/podman.sock:/run/podman/podman.sock \
  -e DASHBOARD_URL="ws://dashboard:8080/ws/daemon" \
  -e MACHINE_ID="gpu-node-001" \
  -e LOG_LEVEL="INFO" \
  -e LOG_FORMAT="json" \
  llm-serve-daemon:latest
```

## Testing

### Run Test Script

```bash
cd /data/home/mgreger/proj/llms/daemon
python test_config.py
```

This validates:
- Missing required variables raise errors
- Defaults apply correctly
- Custom values are loaded
- Validation rejects invalid inputs
- Logging works in both JSON and console formats

### Run Example

```bash
cd /data/home/mgreger/proj/llms/daemon
python example_usage.py
```

This demonstrates practical usage of config and logger.

## Implementation Details

### Pydantic Settings

The `Config` class extends `pydantic_settings.BaseSettings`, which:
- Automatically loads environment variables matching field names
- Supports `.env` file loading
- Provides automatic type conversion and validation
- Raises clear validation errors

### Field Validators

Custom validators ensure:
1. All path fields are absolute paths
2. Interval values are positive and within range
3. Enum values match allowed options

### Logger Configuration

The logger uses `structlog` with:
- ISO timestamp formatting
- Automatic log level inclusion
- Exception info rendering
- Stack trace support
- Configurable output format (JSON or Console)

## Error Handling

### Common Errors

**Missing DASHBOARD_URL:**
```
ValidationError: 1 validation error for Config
DASHBOARD_URL
  Field required [type=missing]
```

**Solution:** Set the required environment variable:
```bash
export DASHBOARD_URL="ws://dashboard:8080/ws/daemon"
```

**Relative Path:**
```
ValidationError: 1 validation error for Config
PROC_PATH
  Value error, PROC_PATH must be an absolute path, got: relative/path
```

**Solution:** Use absolute paths only:
```bash
export PROC_PATH="/host/proc"
```

**Invalid Interval:**
```
ValidationError: 1 validation error for Config
STATS_INTERVAL_SECONDS
  Input should be greater than or equal to 1 [type=greater_than_equal]
```

**Solution:** Use positive values within allowed range:
```bash
export STATS_INTERVAL_SECONDS="6"
```

## Related Documentation

- [Phase 2 Implementation Plan](/data/home/mgreger/proj/llms/docs/implementation-phase-2-daemon-core.md) - Full daemon implementation
- [Daemon Architecture](/data/home/mgreger/proj/llms/docs/architecture-daemon.md) - Architecture overview
- [pyproject.toml](/data/home/mgreger/proj/llms/daemon/pyproject.toml) - Python dependencies
