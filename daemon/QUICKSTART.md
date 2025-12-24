# Configuration Module Quick Start

## Installation

The configuration module is already installed with the daemon dependencies:

```bash
cd /data/home/mgreger/proj/llms/daemon
pip install -e .
```

## Basic Usage

### 1. Set Required Environment Variable

```bash
export DASHBOARD_URL="ws://dashboard.local:8080/ws/daemon"
```

### 2. Import and Use

```python
from src import config, logger

# Access configuration
print(config.DASHBOARD_URL)        # ws://dashboard.local:8080/ws/daemon
print(config.MACHINE_ID)           # auto-generated hostname
print(config.STATS_INTERVAL_SECONDS)  # 6

# Use structured logging
logger.info("daemon_starting", machine_id=config.MACHINE_ID)
logger.error("failed_to_connect", url=config.DASHBOARD_URL, error="timeout")
```

## Configuration Options

### Required
- `DASHBOARD_URL` - Must be set or daemon won't start

### Optional (with defaults)
```bash
export MACHINE_ID="gpu-node-001"              # Default: hostname
export PROC_PATH="/host/proc"                 # Default: /host/proc
export SYS_PATH="/host/sys"                   # Default: /host/sys
export PODMAN_SOCKET="/run/podman/podman.sock"  # Default: /run/podman/podman.sock
export MODEL_PATH="/models"                   # Default: /models
export STATS_INTERVAL_SECONDS="10"            # Default: 6
export HEALTH_CHECK_INTERVAL_SECONDS="3"      # Default: 5
export LOG_LEVEL="DEBUG"                      # Default: INFO
export LOG_FORMAT="console"                   # Default: json
```

## Common Patterns

### Structured Logging

```python
# Always use keyword arguments for context
logger.info("event_name", field1="value1", field2=123, field3=[1, 2, 3])

# Include relevant context
logger.info("stats_collected",
    machine_id=config.MACHINE_ID,
    cpu_load=45.2,
    memory_used=32.5,
    gpu_count=2)

# Error logging with context
try:
    do_something()
except Exception as e:
    logger.error("operation_failed",
        operation="do_something",
        error=str(e),
        exc_info=True)  # Include stack trace
```

### Configuration Access

```python
# Access paths
proc_path = config.PROC_PATH  # Returns Path object
cpu_info = (proc_path / "cpuinfo").read_text()

# Access intervals
await asyncio.sleep(config.STATS_INTERVAL_SECONDS)

# Check log level
if config.LOG_LEVEL == "DEBUG":
    logger.debug("detailed_info", data=huge_object)
```

## Testing

```bash
# Run test suite
cd /data/home/mgreger/proj/llms/daemon
python test_config.py

# Run example
python example_usage.py
```

## Common Issues

### "Field required" Error
```
ValidationError: 1 validation error for Config
DASHBOARD_URL
  Field required
```
**Fix:** Set the required environment variable:
```bash
export DASHBOARD_URL="ws://dashboard:8080/ws/daemon"
```

### "Must be an absolute path" Error
```
ValueError: PROC_PATH must be an absolute path, got: relative/path
```
**Fix:** Use absolute paths only:
```bash
export PROC_PATH="/host/proc"
```

## Container Usage

```bash
podman run \
  -e DASHBOARD_URL="ws://dashboard:8080/ws/daemon" \
  -e MACHINE_ID="gpu-node-001" \
  -e LOG_LEVEL="INFO" \
  -v /proc:/host/proc:ro \
  -v /sys:/host/sys:ro \
  -v /run/podman/podman.sock:/run/podman/podman.sock \
  llm-serve-daemon:latest
```

## More Information

- Full documentation: [CONFIG.md](./CONFIG.md)
- Implementation details: [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)
- Phase 2 plan: [/data/home/mgreger/proj/llms/docs/implementation-phase-2-daemon-core.md](../docs/implementation-phase-2-daemon-core.md)
