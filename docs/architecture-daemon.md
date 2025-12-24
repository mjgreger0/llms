# GPU Daemon - Architecture Document

## Document Information
- **Related PRD**: [llms-prd.md](./llms-prd.md)
- **Component**: GPU Daemon
- **Created**: 2025-12-23
- **Status**: Draft
- **Version**: 1.0

---

## Overview

The GPU Daemon runs on each GPU-equipped machine in the cluster. It acts as a local agent that:

1. **Reports system metrics** to the Dashboard (CPU, memory, GPU stats)
2. **Executes container commands** from the Dashboard (start, stop LLM containers)
3. **Monitors container health** and auto-restarts crashed containers
4. **Maintains connection** to Dashboard with automatic reconnection

The Daemon is a lightweight FastAPI application that runs inside a Podman container with access to host system metrics and the Podman socket for container management.

---

## High-Level Design

### Responsibilities

- Collect and report system metrics every 6 seconds
- Manage LLM container lifecycle (start, stop, restart)
- Monitor container health and auto-restart on failure
- Maintain persistent WebSocket connection to Dashboard
- Execute commands received from Dashboard

### Boundaries

**Owns:**
- Local system metric collection (CPU, memory, GPU)
- Local container lifecycle management
- Container health monitoring and auto-restart
- WebSocket connection management and reconnection

**Does NOT own:**
- Routing decisions (Dashboard decides)
- Eviction decisions (Dashboard decides)
- Request handling (requests go directly to LLM containers)
- Model file management (NFS)

### Key Abstractions

| Concept | Description |
|---------|-------------|
| **Machine** | This host, identified by machine_id |
| **GPU** | A physical GPU, identified by UUID |
| **Container** | A running LLM inference container |
| **Command** | An instruction from Dashboard to execute |
| **Stats Report** | Periodic metrics sent to Dashboard |

---

## Technology Stack

### Language & Framework

- **Python 3.11+** - Async support, type hints
- **FastAPI** - Lightweight, async-native (minimal usage - mostly for structure)
- **Uvicorn** - ASGI server

### Key Libraries

```
# Core
fastapi>=0.104
uvicorn[standard]>=0.24
websockets>=12.0

# System monitoring
pynvml>=11.5          # NVIDIA GPU monitoring
psutil>=5.9           # CPU/memory stats

# Container management
podman-py>=4.8        # Podman SDK

# Utilities
structlog>=23.2       # Structured logging
pydantic>=2.5         # Data validation
```

---

## Application Structure

### Directory Layout

```
daemon/
├── Containerfile
├── pyproject.toml
└── src/
    ├── main.py              # Entry point
    ├── config.py            # Environment-based configuration
    ├── services/
    │   ├── __init__.py
    │   ├── stats_collector.py    # System metrics collection
    │   ├── container_manager.py  # Podman container lifecycle
    │   ├── health_monitor.py     # Container health checking
    │   └── websocket_client.py   # Dashboard connection
    ├── models/
    │   ├── __init__.py
    │   ├── stats.py         # Stats data models
    │   └── commands.py      # Command data models
    └── protocol/
        ├── __init__.py
        └── jsonrpc.py       # JSON-RPC 2.0 helpers
```

---

## System Metrics Collection

### Stats Collector

Collects metrics every 6 seconds using `pynvml` and `psutil`.

```python
class StatsCollector:
    """Collects system metrics from host."""

    def __init__(self, proc_path: str = "/host/proc"):
        self.proc_path = proc_path
        pynvml.nvmlInit()

    async def collect(self) -> MachineStats:
        return MachineStats(
            machine_id=self.machine_id,
            hostname=socket.gethostname(),
            timestamp=datetime.utcnow(),
            cpu=self._collect_cpu(),
            memory=self._collect_memory(),
            network=self._collect_network(),
            gpus=self._collect_gpus(),
            containers=await self._collect_containers()
        )

    def _collect_cpu(self) -> CPUStats:
        # Read from /host/proc for containerized access
        with open(f"{self.proc_path}/loadavg") as f:
            load = float(f.read().split()[0])

        with open(f"{self.proc_path}/cpuinfo") as f:
            cpuinfo = f.read()

        # Parse CPU info
        cores = len([l for l in cpuinfo.splitlines() if l.startswith("processor")])
        threads = cores  # Will refine below

        # Extract model name (e.g., "Intel(R) Xeon(R) Gold 6248R CPU @ 3.00GHz")
        model = ""
        for line in cpuinfo.splitlines():
            if line.startswith("model name"):
                model = line.split(":", 1)[1].strip()
                break

        # Determine manufacturer from model string
        manufacturer = "Unknown"
        if "Intel" in model:
            manufacturer = "Intel"
        elif "AMD" in model:
            manufacturer = "AMD"

        # Get core vs thread count from first processor's siblings
        for line in cpuinfo.splitlines():
            if line.startswith("siblings"):
                threads = int(line.split(":")[1].strip())
            if line.startswith("cpu cores"):
                cores = int(line.split(":")[1].strip())
                break

        return CPUStats(
            manufacturer=manufacturer,
            model=model,
            cores=cores,
            threads=threads,
            load_percent=load * 100 / threads
        )

    def _collect_memory(self) -> MemoryStats:
        with open(f"{self.proc_path}/meminfo") as f:
            info = dict(line.split(":") for line in f.read().splitlines() if ":" in line)
        total = int(info["MemTotal"].strip().split()[0]) / 1024 / 1024
        available = int(info["MemAvailable"].strip().split()[0]) / 1024 / 1024
        return MemoryStats(
            total_gb=total,
            used_gb=total - available,
            available_gb=available
        )

    def _collect_network(self) -> list[NetworkInterfaceStats]:
        """
        Collect network interface stats including link speed.

        Uses /sys/class/net for interface info and psutil for traffic counters.
        Computes rate from delta since last collection.
        """
        interfaces = []
        net_io = psutil.net_io_counters(pernic=True)

        for iface in os.listdir("/sys/class/net"):
            # Skip loopback and virtual interfaces
            if iface.startswith(("lo", "veth", "docker", "br-", "virbr")):
                continue

            try:
                # Get interface details from /sys/class/net/{iface}/
                iface_path = f"/sys/class/net/{iface}"

                # MAC address
                with open(f"{iface_path}/address") as f:
                    mac = f.read().strip()

                # Link speed (Mbps) - may not exist for all interfaces
                try:
                    with open(f"{iface_path}/speed") as f:
                        speed = int(f.read().strip())
                except (FileNotFoundError, ValueError):
                    speed = 0

                # MTU
                with open(f"{iface_path}/mtu") as f:
                    mtu = int(f.read().strip())

                # Operational state
                with open(f"{iface_path}/operstate") as f:
                    is_up = f.read().strip() == "up"

                # IP addresses (via psutil)
                addrs = psutil.net_if_addrs().get(iface, [])
                ip_addresses = [
                    addr.address for addr in addrs
                    if addr.family in (socket.AF_INET, socket.AF_INET6)
                    and not addr.address.startswith("fe80:")  # Skip link-local IPv6
                ]

                # Traffic counters
                counters = net_io.get(iface)
                bytes_sent = counters.bytes_sent if counters else 0
                bytes_recv = counters.bytes_recv if counters else 0

                # Compute rate from previous sample (stored in self._prev_net)
                prev = self._prev_net.get(iface, {})
                time_delta = (datetime.utcnow() - prev.get("time", datetime.utcnow())).total_seconds()
                if time_delta > 0:
                    bytes_sent_rate = (bytes_sent - prev.get("sent", bytes_sent)) / time_delta
                    bytes_recv_rate = (bytes_recv - prev.get("recv", bytes_recv)) / time_delta
                else:
                    bytes_sent_rate = 0.0
                    bytes_recv_rate = 0.0

                # Store for next delta calculation
                self._prev_net[iface] = {
                    "time": datetime.utcnow(),
                    "sent": bytes_sent,
                    "recv": bytes_recv
                }

                interfaces.append(NetworkInterfaceStats(
                    interface=iface,
                    mac_address=mac,
                    ip_addresses=ip_addresses,
                    speed_mbps=speed,
                    mtu=mtu,
                    is_up=is_up,
                    bytes_sent=bytes_sent,
                    bytes_recv=bytes_recv,
                    bytes_sent_rate=bytes_sent_rate,
                    bytes_recv_rate=bytes_recv_rate
                ))
            except (FileNotFoundError, IOError, OSError):
                continue

        return interfaces

    def _collect_gpus(self) -> list[GPUStats]:
        gpus = []
        for i in range(pynvml.nvmlDeviceGetCount()):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)

            # Basic identification
            uuid = pynvml.nvmlDeviceGetUUID(handle)
            chip_model = pynvml.nvmlDeviceGetName(handle)  # e.g., "NVIDIA GeForce RTX 4090"

            # Memory info
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)

            # Utilization
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)

            # Temperature
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)

            # Power info
            try:
                power_draw = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000  # mW to W
                power_limit = pynvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000
            except pynvml.NVMLError:
                power_draw = 0.0
                power_limit = 0.0

            # PCI bus ID for identifying card manufacturer
            pci_info = pynvml.nvmlDeviceGetPciInfo(handle)
            pci_bus_id = pci_info.busId.decode() if isinstance(pci_info.busId, bytes) else pci_info.busId

            # Get card manufacturer from PCI subsystem vendor
            card_manufacturer = self._get_card_manufacturer(pci_bus_id)

            # Serial number (if available)
            try:
                serial = pynvml.nvmlDeviceGetSerial(handle)
            except pynvml.NVMLError:
                serial = None

            # Chip manufacturer (always NVIDIA for now, but future-proof)
            chip_manufacturer = "NVIDIA"

            gpus.append(GPUStats(
                index=i,
                uuid=uuid,
                chip_manufacturer=chip_manufacturer,
                chip_model=chip_model,
                card_manufacturer=card_manufacturer,
                pci_bus_id=pci_bus_id,
                serial=serial,
                memory_total_gb=mem.total / 1024**3,
                memory_used_gb=mem.used / 1024**3,
                utilization_percent=util.gpu,
                temperature_c=temp,
                power_draw_w=power_draw,
                power_limit_w=power_limit,
                model_loaded=self._get_model_for_gpu(i)
            ))
        return gpus

    def _get_card_manufacturer(self, pci_bus_id: str) -> str:
        """
        Get card manufacturer (e.g., eVGA, MSI, ASUS) from PCI subsystem vendor.

        The PCI subsystem vendor ID identifies the card manufacturer, not the chip maker.
        We read from /sys/bus/pci/devices/{bus_id}/subsystem_vendor and look up the name.
        """
        # Convert PCI bus ID format: "0000:01:00.0" -> "0000:01:00.0"
        sys_path = f"/sys/bus/pci/devices/{pci_bus_id}/subsystem_vendor"

        try:
            with open(sys_path) as f:
                vendor_id = f.read().strip()  # e.g., "0x3842" for eVGA

            return self._pci_vendor_lookup(vendor_id)
        except (FileNotFoundError, IOError):
            return "Unknown"

    def _pci_vendor_lookup(self, vendor_id: str) -> str:
        """
        Look up PCI vendor name from vendor ID.

        Common GPU card manufacturers:
        """
        # Common GPU card manufacturers (subsystem vendors)
        vendors = {
            "0x3842": "eVGA",
            "0x1462": "MSI",
            "0x1043": "ASUS",
            "0x10de": "NVIDIA",      # Reference/Founders Edition
            "0x1458": "Gigabyte",
            "0x196e": "PNY",
            "0x1569": "Palit",
            "0x1682": "XFX",
            "0x148c": "PowerColor",
            "0x1da2": "Sapphire",
            "0x1028": "Dell",
            "0x103c": "HP",
            "0x17aa": "Lenovo",
            "0x1849": "ASRock",
            "0x19da": "Zotac",
            "0x1b4c": "Colorful",
            "0x7377": "Colorful",
            "0x1d97": "Shenzhen Lianrui",  # Some Chinese brands
        }
        return vendors.get(vendor_id.lower(), f"Unknown ({vendor_id})")

    async def _collect_containers(self) -> list[ContainerStats]:
        # Via podman-py
        containers = []
        for c in self.podman.containers.list():
            if c.labels.get("llm-serve") == "true":
                containers.append(ContainerStats(
                    id=c.id[:12],
                    model=c.labels.get("model"),
                    runtime=c.labels.get("runtime"),
                    gpus=json.loads(c.labels.get("gpus", "[]")),
                    status=c.status,
                    uptime_seconds=self._calculate_uptime(c)
                ))
        return containers
```

### Data Models

```python
@dataclass
class MachineStats:
    machine_id: str
    hostname: str
    timestamp: datetime
    cpu: CPUStats
    memory: MemoryStats
    network: list[NetworkInterfaceStats]
    gpus: list[GPUStats]
    containers: list[ContainerStats]

@dataclass
class CPUStats:
    manufacturer: str       # e.g., "Intel", "AMD"
    model: str              # e.g., "Intel(R) Xeon(R) Gold 6248R CPU @ 3.00GHz"
    cores: int
    threads: int
    load_percent: float

@dataclass
class MemoryStats:
    total_gb: float
    used_gb: float
    available_gb: float

@dataclass
class NetworkInterfaceStats:
    interface: str           # e.g., "eth0", "enp5s0"
    mac_address: str
    ip_addresses: list[str]  # IPv4 and IPv6
    speed_mbps: int          # Link speed (e.g., 10000 for 10Gbps)
    mtu: int
    is_up: bool
    bytes_sent: int          # Total bytes since boot
    bytes_recv: int
    bytes_sent_rate: float   # Bytes/sec (computed from delta)
    bytes_recv_rate: float

@dataclass
class GPUStats:
    index: int
    uuid: str
    chip_manufacturer: str   # e.g., "NVIDIA"
    chip_model: str          # e.g., "GeForce RTX 4090"
    card_manufacturer: str   # e.g., "eVGA", "MSI", "ASUS" (from PCI subsystem)
    pci_bus_id: str          # e.g., "0000:01:00.0"
    serial: str | None       # Board serial if available
    memory_total_gb: float
    memory_used_gb: float
    utilization_percent: int
    temperature_c: int
    power_draw_w: float
    power_limit_w: float
    model_loaded: str | None

@dataclass
class ContainerStats:
    id: str
    model: str
    runtime: str
    gpus: list[int]
    status: str
    uptime_seconds: int
```

---

## Container Management

### Container Manager

Manages LLM container lifecycle using `podman-py`.

```python
from podman import PodmanClient

class ContainerManager:
    """Manages LLM containers via Podman."""

    def __init__(self, socket_path: str = "/run/podman/podman.sock"):
        self.client = PodmanClient(base_url=f"unix://{socket_path}")
        self.running_containers: dict[str, Container] = {}

    async def start_container(self, config: ContainerConfig) -> str:
        """Start an LLM container with the given configuration."""
        container_name = f"llm-{config.model_quant}-{uuid.uuid4().hex[:8]}"

        # Build podman run arguments
        container = self.client.containers.run(
            image=config.image,
            name=container_name,
            detach=True,
            remove=False,
            ports={"8000/tcp": None},  # Dynamic port assignment
            environment=self._build_env(config),
            command=self._build_command(config),
            devices=self._build_gpu_devices(config.gpus),
            volumes={
                config.model_path: {"bind": "/models", "mode": "ro"}
            },
            labels={
                "llm-serve": "true",
                "model": config.model_quant,
                "runtime": config.runtime,
                "gpus": json.dumps(config.gpus)
            },
            # Resource limits
            shm_size="16g",  # Shared memory for GPU operations
        )

        self.running_containers[config.model_quant] = container
        return container.id

    def _build_gpu_devices(self, gpu_indices: list[int]) -> list[str]:
        """Build GPU device specifications for podman."""
        # nvidia-container-toolkit format
        return [f"nvidia.com/gpu={i}" for i in gpu_indices]

    def _build_env(self, config: ContainerConfig) -> dict[str, str]:
        """Build environment variables for the container."""
        env = {
            "CUDA_VISIBLE_DEVICES": ",".join(str(i) for i in config.gpus),
        }
        if config.runtime == "vllm":
            env["VLLM_WORKER_MULTIPROC_METHOD"] = "spawn"
        return env

    def _build_command(self, config: ContainerConfig) -> list[str]:
        """Build the container command based on runtime."""
        if config.runtime == "vllm":
            return [
                "--model", f"/models/{config.model_path}",
                "--max-model-len", str(config.context_length),
                "--tensor-parallel-size", str(config.tensor_parallel),
                "--pipeline-parallel-size", str(config.pipeline_parallel),
                "--max-num-seqs", str(config.max_parallel),
                "--host", "0.0.0.0",
                "--port", "8000",
            ]
        elif config.runtime == "sglang":
            return [
                "--model-path", f"/models/{config.model_path}",
                "--context-length", str(config.context_length),
                "--tp", str(config.tensor_parallel),
                "--host", "0.0.0.0",
                "--port", "8000",
            ]
        # Add llamacpp support as needed
        raise ValueError(f"Unknown runtime: {config.runtime}")

    async def stop_container(self, model_quant: str, evicting: bool = False) -> None:
        """Stop a running LLM container."""
        if model_quant not in self.running_containers:
            return

        container = self.running_containers[model_quant]
        container.stop(timeout=30)
        container.remove()
        del self.running_containers[model_quant]

    def get_container_port(self, model_quant: str) -> int | None:
        """Get the exposed port for a running container."""
        if model_quant not in self.running_containers:
            return None
        container = self.running_containers[model_quant]
        ports = container.ports.get("8000/tcp", [])
        if ports:
            return int(ports[0]["HostPort"])
        return None
```

### Container Configuration

```python
@dataclass
class ContainerConfig:
    model_quant: str           # e.g., "qwen2.5-72b-instruct-awq"
    model_path: str            # Path within NFS mount
    image: str                 # e.g., "vllm/vllm-openai:latest"
    runtime: str               # vllm, sglang, llamacpp
    gpus: list[int]            # GPU indices to use
    context_length: int
    max_parallel: int
    tensor_parallel: int
    pipeline_parallel: int
    extra_args: dict | None
```

---

## Health Monitoring

### Health Monitor

Monitors container health and auto-restarts crashed containers.

```python
class HealthMonitor:
    """Monitors container health and restarts on failure."""

    def __init__(
        self,
        container_manager: ContainerManager,
        websocket_client: WebSocketClient
    ):
        self.container_manager = container_manager
        self.websocket_client = websocket_client
        self.health_check_interval = 5  # seconds
        self.containers_starting: set[str] = set()
        self.containers_evicting: set[str] = set()

    async def run(self):
        """Main health monitoring loop."""
        while True:
            await self.check_all_containers()
            await asyncio.sleep(self.health_check_interval)

    async def check_all_containers(self):
        """Check health of all running containers."""
        for model_quant, container in self.container_manager.running_containers.items():
            # Skip containers being evicted
            if model_quant in self.containers_evicting:
                continue

            status = await self.check_container_health(container)

            if status == "crashed":
                await self.handle_crash(model_quant, container)
            elif status == "healthy":
                # Container is fine
                pass

    async def check_container_health(self, container) -> str:
        """Check if container is healthy."""
        container.reload()

        if container.status != "running":
            return "crashed"

        # For containers that have been running a while, check HTTP health
        if self._container_age_seconds(container) > 30:
            port = self.container_manager.get_container_port(container.labels["model"])
            if port:
                try:
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(
                            f"http://localhost:{port}/health",
                            timeout=5.0
                        )
                        if resp.status_code == 200:
                            return "healthy"
                except Exception:
                    pass
                return "unhealthy"

        return "starting"

    async def handle_crash(self, model_quant: str, container):
        """Handle a crashed container by restarting it."""
        logger.warning("container_crashed", model=model_quant, container_id=container.id[:12])

        # Notify Dashboard
        await self.websocket_client.send_notification(
            "container.status",
            {"model": model_quant, "status": "crashed", "restarting": True}
        )

        # Get the config to restart
        config = self._get_stored_config(model_quant)
        if config:
            # Remove crashed container
            try:
                container.remove(force=True)
            except Exception:
                pass

            # Restart
            await self.container_manager.start_container(config)

            logger.info("container_restarted", model=model_quant)
            await self.websocket_client.send_notification(
                "container.status",
                {"model": model_quant, "status": "restarting"}
            )

    def mark_evicting(self, model_quant: str):
        """Mark container as being evicted (don't restart on stop)."""
        self.containers_evicting.add(model_quant)

    def unmark_evicting(self, model_quant: str):
        """Remove eviction mark."""
        self.containers_evicting.discard(model_quant)
```

### Startup Health Polling

When Dashboard sends a `container.start` command, Daemon polls health at 1s intervals:

```python
async def wait_for_healthy(self, model_quant: str, timeout: int = 300) -> bool:
    """Wait for container to become healthy."""
    start_time = time.time()
    port = None

    while time.time() - start_time < timeout:
        # Get port once container is running
        if port is None:
            port = self.container_manager.get_container_port(model_quant)
            if port is None:
                await asyncio.sleep(1)
                continue

        # Poll health endpoint
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"http://localhost:{port}/health",
                    timeout=5.0
                )
                if resp.status_code == 200:
                    return True
        except Exception:
            pass

        await asyncio.sleep(1)

    return False
```

---

## WebSocket Client

### Connection Management

Maintains persistent connection to Dashboard with automatic reconnection.

```python
class WebSocketClient:
    """Manages WebSocket connection to Dashboard."""

    def __init__(self, dashboard_url: str, machine_id: str):
        self.dashboard_url = dashboard_url
        self.machine_id = machine_id
        self.websocket: WebSocket | None = None
        self.connected = False
        self.pending_requests: dict[int, asyncio.Future] = {}
        self.request_id = 0

    async def connect(self):
        """Connect to Dashboard with exponential backoff."""
        backoff = 1.0
        max_backoff = 60.0
        jitter = 0.5

        while True:
            try:
                async with websockets.connect(self.dashboard_url) as ws:
                    self.websocket = ws
                    self.connected = True
                    logger.info("connected_to_dashboard", url=self.dashboard_url)

                    # Send registration
                    await self._send_registration()

                    # Reset backoff on successful connection
                    backoff = 1.0

                    # Handle messages
                    await self._message_loop()

            except Exception as e:
                logger.warning("connection_failed", error=str(e), backoff=backoff)
                self.connected = False
                self.websocket = None

                # Exponential backoff with jitter
                sleep_time = backoff + random.uniform(-jitter, jitter)
                await asyncio.sleep(sleep_time)
                backoff = min(backoff * 2, max_backoff)

    async def _send_registration(self):
        """Send initial registration message."""
        # Collect current state to send with registration
        stats = await stats_collector.collect()

        await self.send_notification("daemon.register", {
            "machine_id": self.machine_id,
            "hostname": socket.gethostname(),
            "stats": stats.to_dict()
        })

    async def _message_loop(self):
        """Process incoming messages from Dashboard."""
        async for message in self.websocket:
            data = json.loads(message)
            await self._handle_message(data)

    async def _handle_message(self, message: dict):
        """Handle a JSON-RPC message from Dashboard."""
        # Response to our request
        if "result" in message or "error" in message:
            request_id = message.get("id")
            if request_id in self.pending_requests:
                self.pending_requests[request_id].set_result(message)
            return

        # Request from Dashboard
        method = message.get("method")
        params = message.get("params", {})
        request_id = message.get("id")

        result = await self._dispatch_command(method, params)

        # Send response if request had an ID
        if request_id is not None:
            await self._send_response(request_id, result)

    async def _dispatch_command(self, method: str, params: dict) -> dict:
        """Dispatch a command to the appropriate handler."""
        handlers = {
            "container.start": self._handle_start,
            "container.stop": self._handle_stop,
            "container.restart": self._handle_restart,
        }

        handler = handlers.get(method)
        if handler:
            return await handler(params)
        else:
            return {"error": f"Unknown method: {method}"}

    async def _handle_start(self, params: dict) -> dict:
        """Handle container.start command."""
        config = ContainerConfig(**params)

        try:
            container_id = await container_manager.start_container(config)

            # Wait for healthy (async, report status along the way)
            asyncio.create_task(self._monitor_startup(config.model_quant))

            return {"container_id": container_id, "status": "starting"}
        except Exception as e:
            logger.error("container_start_failed", error=str(e), model=config.model_quant)
            return {"error": str(e)}

    async def _monitor_startup(self, model_quant: str):
        """Monitor container startup and report when ready."""
        healthy = await health_monitor.wait_for_healthy(model_quant)

        if healthy:
            port = container_manager.get_container_port(model_quant)
            await self.send_notification("container.status", {
                "model": model_quant,
                "status": "ready",
                "port": port
            })
        else:
            await self.send_notification("container.status", {
                "model": model_quant,
                "status": "failed",
                "reason": "health_check_timeout"
            })

    async def _handle_stop(self, params: dict) -> dict:
        """Handle container.stop command."""
        model_quant = params["model"]
        evicting = params.get("evicting", False)

        if evicting:
            health_monitor.mark_evicting(model_quant)

        try:
            await container_manager.stop_container(model_quant, evicting=evicting)
            return {"status": "stopped"}
        except Exception as e:
            return {"error": str(e)}
        finally:
            if evicting:
                health_monitor.unmark_evicting(model_quant)

    async def send_notification(self, method: str, params: dict):
        """Send a notification (no response expected)."""
        if not self.connected:
            return

        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        await self.websocket.send(json.dumps(message))

    async def send_request(self, method: str, params: dict) -> dict:
        """Send a request and wait for response."""
        if not self.connected:
            raise ConnectionError("Not connected to Dashboard")

        self.request_id += 1
        request_id = self.request_id

        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id
        }

        future = asyncio.Future()
        self.pending_requests[request_id] = future

        await self.websocket.send(json.dumps(message))

        try:
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
        finally:
            del self.pending_requests[request_id]
```

---

## Main Application

### Entry Point

```python
# src/main.py
import asyncio
from config import Config
from services.stats_collector import StatsCollector
from services.container_manager import ContainerManager
from services.health_monitor import HealthMonitor
from services.websocket_client import WebSocketClient

config = Config()

# Initialize services
stats_collector = StatsCollector(proc_path=config.proc_path)
container_manager = ContainerManager(socket_path=config.podman_socket)
websocket_client = WebSocketClient(config.dashboard_url, config.machine_id)
health_monitor = HealthMonitor(container_manager, websocket_client)

async def stats_loop():
    """Send stats to Dashboard every 6 seconds."""
    while True:
        if websocket_client.connected:
            stats = await stats_collector.collect()
            await websocket_client.send_notification("stats.report", stats.to_dict())
        await asyncio.sleep(6)

async def main():
    """Main entry point."""
    logger.info("daemon_starting", machine_id=config.machine_id)

    # Start background tasks
    asyncio.create_task(health_monitor.run())
    asyncio.create_task(stats_loop())

    # Connect to Dashboard (blocking, with reconnection)
    await websocket_client.connect()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Configuration

All configuration via environment variables:

```bash
# Required
DASHBOARD_URL=ws://192.168.0.10:8080/ws/daemon
MACHINE_ID=gpu-server-b   # Auto-generated from hostname if not set

# Paths (for containerized access to host)
PROC_PATH=/host/proc
SYS_PATH=/host/sys
PODMAN_SOCKET=/run/podman/podman.sock

# Model storage
MODEL_PATH=/data/projects/ai/models

# Intervals
STATS_INTERVAL_SECONDS=6
HEALTH_CHECK_INTERVAL_SECONDS=5

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## Deployment

### Container Requirements

The Daemon container needs special access to host resources:

| Resource | Mount/Flag | Purpose |
|----------|------------|---------|
| `/proc` | `-v /proc:/host/proc:ro` | CPU, memory stats |
| `/sys` | `-v /sys:/host/sys:ro` | Device information |
| Podman socket | `-v /run/podman/podman.sock:/run/podman/podman.sock` | Container management |
| GPUs | `--device nvidia.com/gpu=all` | GPU stats via pynvml |
| NFS models | `-v /data/projects/ai/models:/models:ro` | Model files (passed to LLM containers) |

### Prerequisites on Host

```bash
# 1. Install nvidia-container-toolkit
sudo dnf install nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=podman

# 2. Enable Podman socket (user or system level)
systemctl --user enable --now podman.socket
# Or for system-level:
sudo systemctl enable --now podman.socket

# 3. Verify GPU access
podman run --rm --device nvidia.com/gpu=all nvidia/cuda:12.0-base nvidia-smi
```

### Container Launch

```bash
podman run -d \
  --name llm-serve-daemon \
  --restart=always \
  -v /proc:/host/proc:ro \
  -v /sys:/host/sys:ro \
  -v /run/podman/podman.sock:/run/podman/podman.sock \
  -v /data/projects/ai/models:/models:ro \
  --device nvidia.com/gpu=all \
  -e DASHBOARD_URL=ws://192.168.0.10:8080/ws/daemon \
  -e MACHINE_ID=gpu-server-b \
  -e PROC_PATH=/host/proc \
  -e MODEL_PATH=/models \
  llm-serve-daemon:latest
```

### Containerfile

```dockerfile
FROM python:3.11-slim

# Install NVIDIA tools for pynvml
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy source
COPY src/ ./src/

# Run
CMD ["python", "-m", "src.main"]
```

### Systemd Service (Alternative)

For boot startup without container:

```ini
# /etc/systemd/system/llm-serve-daemon.service
[Unit]
Description=LLM Serve Daemon
After=network-online.target podman.socket
Wants=network-online.target

[Service]
Type=simple
Environment=DASHBOARD_URL=ws://192.168.0.10:8080/ws/daemon
ExecStart=/usr/bin/podman run --rm \
  --name llm-serve-daemon \
  -v /proc:/host/proc:ro \
  -v /sys:/host/sys:ro \
  -v /run/podman/podman.sock:/run/podman/podman.sock \
  -v /data/projects/ai/models:/models:ro \
  --device nvidia.com/gpu=all \
  -e DASHBOARD_URL \
  llm-serve-daemon:latest
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Logging

Structured JSON logging:

```python
import structlog

logger = structlog.get_logger()

# Examples
logger.info("stats_collected", gpus=4, containers=2)
logger.info("container_started", model="qwen2.5-72b-instruct-awq", gpus=[0, 1])
logger.warning("health_check_failed", model="llama-70b", port=8001)
logger.error("container_crash", model="mistral-7b", error="OOM killed")
```

---

## Error Handling

### Connection Errors

- WebSocket disconnect: Automatic reconnection with exponential backoff + jitter
- Dashboard unreachable: Keep retrying, containers continue running
- Network partition: Same as disconnect, containers maintain status quo

### Container Errors

- Container crash: Auto-restart (unless being evicted)
- Health check timeout: Report to Dashboard, let Dashboard decide
- Start failure: Report error to Dashboard, mark GPUs as free

### Resource Errors

- GPU OOM: Container crashes, auto-restart may fail again (needs Dashboard intervention)
- Disk full: Container start fails, report to Dashboard

---

## Related Documents

- [Architecture Overview](./architecture-overview.md)
- [Dashboard Architecture](./architecture-dashboard.md)
- [Container Library](./architecture-containers.md)
- [Product Requirements](./llms-prd.md)
