# Phase 2: Daemon Core - Implementation Plan

## Document Information
- **Phase**: 2 of 8
- **Component**: GPU Daemon
- **Related Architecture**: [architecture-daemon.md](./architecture-daemon.md)
- **Dependencies**: Phase 1 (Dev Environment Setup)
- **Created**: 2025-12-23
- **Status**: Complete
- **Completed**: 2025-12-23

---

## Phase Overview

**Goal**: Implement stats collection and container management on GPU machines

**Deliverables**:
- StatsCollector service (CPU, memory, network, GPU via pynvml)
- ContainerManager service (Podman operations via podman-py)
- HealthMonitor service (container health checking)
- Data models (MachineStats, GPUStats, etc.)
- Configuration via environment variables

**Exit Criteria**:
- [x] Daemon collects all stats matching architecture schema
- [x] Can start/stop Podman containers
- [x] Stats output validated against examples in arch doc
- [x] Environment variable configuration works
- [x] Health monitoring detects crashed containers

---

## Progress Tracking

**Overall Progress**: 47/47 tasks completed (100%)

### By Section:
- [x] 1. Configuration Module: 4/4 tasks (100%)
- [x] 2. Data Models: 7/7 tasks (100%)
- [x] 3. StatsCollector Service: 16/16 tasks (100%)
- [x] 4. ContainerManager Service: 9/9 tasks (100%)
- [x] 5. HealthMonitor Service: 6/6 tasks (100%)
- [x] 6. Main Entrypoint: 5/5 tasks (100%)

---

## Section 1: Configuration Module

**Purpose**: Load and validate all configuration from environment variables

**Progress**: 4/4 tasks (100%)

---

#### Task 1.1: Create Config Class
- [x] **Status**: Complete
- **Description**: Implement environment variable loader with validation and defaults
- **Acceptance Criteria**:
  - [x] All required variables loaded (DASHBOARD_URL, MACHINE_ID)
  - [x] Optional variables have sensible defaults
  - [x] Validation raises clear errors for missing/invalid values
  - [x] Auto-generates MACHINE_ID from hostname if not provided
- **Technical Approach**:
  - Use Pydantic Settings for automatic env loading and validation
  - Provide defaults for paths, intervals, logging
  - Implement hostname-based machine_id fallback
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/config.py` - Main Config class
- **Dependencies**: None
- **Complexity**: S

---

#### Task 1.2: Define Environment Variable Schema
- [x] **Status**: Complete
- **Description**: Document all environment variables and their defaults
- **Acceptance Criteria**:
  - [x] Required variables clearly marked
  - [x] Defaults match architecture doc
  - [x] Type validation for each variable
  - [x] Path variables accept absolute paths only
- **Technical Approach**:
  - Use Pydantic Field with description and validation
  - Required: DASHBOARD_URL
  - Optional with defaults: MACHINE_ID (hostname), PROC_PATH (/host/proc), SYS_PATH (/host/sys), PODMAN_SOCKET (/run/podman/podman.sock), MODEL_PATH (/models), STATS_INTERVAL_SECONDS (6), HEALTH_CHECK_INTERVAL_SECONDS (5), LOG_LEVEL (INFO), LOG_FORMAT (json)
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/config.py` - Environment schema
- **Dependencies**: Task 1.1
- **Complexity**: S

---

#### Task 1.3: Implement Logging Configuration
- [x] **Status**: Complete
- **Description**: Configure structured logging based on LOG_LEVEL and LOG_FORMAT
- **Acceptance Criteria**:
  - [x] JSON format works (structlog)
  - [x] Log level can be set via env var
  - [x] Logs include timestamp, level, message, context
  - [x] Logger available as module-level import
- **Technical Approach**:
  - Use structlog with JSON renderer
  - Configure based on Config.log_level and Config.log_format
  - Set up in config module for global access
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/config.py` - Setup logging
  - [x] `/data/home/mgreger/proj/llms/daemon/src/logger.py` - Logger instance
- **Dependencies**: Task 1.1
- **Complexity**: S

---

#### Task 1.4: Test Configuration Loading
- [x] **Status**: Complete
- **Description**: Validate config loads correctly with various env combinations
- **Acceptance Criteria**:
  - [x] Missing DASHBOARD_URL raises error
  - [x] Defaults apply when optional vars not set
  - [x] MACHINE_ID auto-generates from hostname
  - [x] Invalid values (e.g., negative intervals) rejected
- **Technical Approach**:
  - Manual testing with different env vars
  - Test missing required, test defaults, test validation
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/config.py` - Add validation
- **Dependencies**: Tasks 1.1, 1.2
- **Complexity**: S

---

## Section 2: Data Models

**Purpose**: Define Pydantic models matching architecture schema for stats reporting

**Progress**: 7/7 tasks (100%)

---

#### Task 2.1: Create CPUStats Model
- [x] **Status**: Complete
- **Description**: Pydantic model for CPU information
- **Acceptance Criteria**:
  - [x] Fields: manufacturer, model, cores, threads, load_percent
  - [x] Types match architecture doc (str, int, float)
  - [x] Serializes to JSON matching example in PRD
- **Technical Approach**:
  - Use dataclass or Pydantic BaseModel
  - Match exact schema from architecture-daemon.md lines 420-426
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/models/stats.py` - CPUStats class
- **Dependencies**: None
- **Complexity**: S

---

#### Task 2.2: Create MemoryStats Model
- [x] **Status**: Complete
- **Description**: Pydantic model for memory information
- **Acceptance Criteria**:
  - [x] Fields: total_gb, used_gb, available_gb
  - [x] All values in gigabytes (float)
  - [x] Matches architecture doc schema
- **Technical Approach**:
  - Simple dataclass with three float fields
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/models/stats.py` - MemoryStats class
- **Dependencies**: None
- **Complexity**: S

---

#### Task 2.3: Create NetworkInterfaceStats Model
- [x] **Status**: Complete
- **Description**: Pydantic model for network interface metrics
- **Acceptance Criteria**:
  - [x] Fields: interface, mac_address, ip_addresses, speed_mbps, mtu, is_up, bytes_sent, bytes_recv, bytes_sent_rate, bytes_recv_rate
  - [x] ip_addresses is list of strings
  - [x] Rate fields are float (bytes/sec)
  - [x] Matches architecture doc lines 434-445
- **Technical Approach**:
  - Dataclass with all specified fields
  - ip_addresses: list[str]
  - rates: float
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/models/stats.py` - NetworkInterfaceStats class
- **Dependencies**: None
- **Complexity**: S

---

#### Task 2.4: Create GPUStats Model
- [x] **Status**: Complete
- **Description**: Pydantic model for GPU metrics
- **Acceptance Criteria**:
  - [x] Fields: index, uuid, chip_manufacturer, chip_model, card_manufacturer, pci_bus_id, serial, memory_total_gb, memory_used_gb, utilization_percent, temperature_c, power_draw_w, power_limit_w, model_loaded
  - [x] Optional fields: serial (str | None), model_loaded (str | None)
  - [x] Matches architecture doc lines 447-462
- **Technical Approach**:
  - Dataclass with all specified fields
  - Use Optional for nullable fields
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/models/stats.py` - GPUStats class
- **Dependencies**: None
- **Complexity**: S

---

#### Task 2.5: Create ContainerStats Model
- [x] **Status**: Complete
- **Description**: Pydantic model for container information
- **Acceptance Criteria**:
  - [x] Fields: id, model, runtime, gpus, status, uptime_seconds
  - [x] gpus is list[int]
  - [x] Matches architecture doc lines 464-471
- **Technical Approach**:
  - Dataclass with specified fields
  - gpus: list[int]
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/models/stats.py` - ContainerStats class
- **Dependencies**: None
- **Complexity**: S

---

#### Task 2.6: Create MachineStats Model
- [x] **Status**: Complete
- **Description**: Top-level Pydantic model aggregating all stats
- **Acceptance Criteria**:
  - [x] Fields: machine_id, hostname, timestamp, cpu, memory, network, gpus, containers
  - [x] Nested models for cpu, memory, etc.
  - [x] network is list[NetworkInterfaceStats]
  - [x] gpus is list[GPUStats]
  - [x] containers is list[ContainerStats]
  - [x] to_dict() method for JSON serialization
  - [x] Matches architecture doc lines 409-418
- **Technical Approach**:
  - Aggregate all other stats models
  - Use datetime for timestamp
  - Implement to_dict() using Pydantic's dict() or custom serialization
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/models/stats.py` - MachineStats class
- **Dependencies**: Tasks 2.1-2.5
- **Complexity**: M

---

#### Task 2.7: Create ContainerConfig Model
- [x] **Status**: Complete
- **Description**: Model for LLM container launch configuration
- **Acceptance Criteria**:
  - [x] Fields: model_quant, model_path, image, runtime, gpus, context_length, max_parallel, tensor_parallel, pipeline_parallel, extra_args
  - [x] Matches architecture doc lines 583-595
  - [x] All fields required except extra_args (Optional)
- **Technical Approach**:
  - Dataclass matching spec from architecture
  - extra_args: dict | None = None
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/models/commands.py` - ContainerConfig class
- **Dependencies**: None
- **Complexity**: S

---

## Section 3: StatsCollector Service

**Purpose**: Collect CPU, memory, network, and GPU stats from host system

**Progress**: 16/16 tasks (100%)

---

#### Task 3.1: Create StatsCollector Skeleton
- [x] **Status**: Complete
- **Description**: Set up StatsCollector class with initialization
- **Acceptance Criteria**:
  - [x] Class initializes with proc_path parameter
  - [x] pynvml.nvmlInit() called in __init__
  - [x] collect() method returns MachineStats
  - [x] Basic structure matches architecture doc lines 126-143
- **Technical Approach**:
  - Import pynvml, initialize GPU access
  - Store proc_path for later use
  - Create async collect() method
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/stats_collector.py` - StatsCollector class
- **Dependencies**: Task 2.6 (MachineStats model)
- **Complexity**: S

---

#### Task 3.2: Implement CPU Stats Collection
- [x] **Status**: Complete
- **Description**: Read CPU info from /proc/cpuinfo and /proc/loadavg
- **Acceptance Criteria**:
  - [x] Reads from {proc_path}/cpuinfo and {proc_path}/loadavg
  - [x] Extracts manufacturer (Intel/AMD) from model name
  - [x] Counts cores and threads correctly
  - [x] Calculates load_percent from loadavg
  - [x] Returns CPUStats instance
  - [x] Handles missing/malformed files gracefully
- **Technical Approach**:
  - Parse /proc/cpuinfo for model name, core count, siblings
  - Read first value from /proc/loadavg
  - Calculate load_percent = (load * 100) / threads
  - Follow implementation in architecture doc lines 145-185
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/stats_collector.py` - _collect_cpu() method
- **Dependencies**: Tasks 2.1, 3.1
- **Complexity**: M

---

#### Task 3.3: Implement Memory Stats Collection
- [x] **Status**: Complete
- **Description**: Read memory info from /proc/meminfo
- **Acceptance Criteria**:
  - [x] Reads from {proc_path}/meminfo
  - [x] Extracts MemTotal and MemAvailable
  - [x] Converts KB to GB correctly
  - [x] Calculates used_gb = total - available
  - [x] Returns MemoryStats instance
- **Technical Approach**:
  - Parse /proc/meminfo for MemTotal and MemAvailable lines
  - Convert kB values to GB (/ 1024 / 1024)
  - Follow implementation in architecture doc lines 187-196
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/stats_collector.py` - _collect_memory() method
- **Dependencies**: Tasks 2.2, 3.1
- **Complexity**: S

---

#### Task 3.4: Implement Network Interface Discovery
- [x] **Status**: Complete
- **Description**: List physical network interfaces from /sys/class/net
- **Acceptance Criteria**:
  - [x] Iterates /sys/class/net directory
  - [x] Filters out loopback (lo) and virtual interfaces (veth, docker, br-, virbr)
  - [x] Returns list of physical interface names
  - [x] Handles permission errors gracefully
- **Technical Approach**:
  - Use os.listdir("/sys/class/net")
  - Skip interfaces starting with excluded prefixes
  - See architecture doc lines 208-211
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/stats_collector.py` - Network filtering in _collect_network()
- **Dependencies**: Task 3.1
- **Complexity**: S

---

#### Task 3.5: Implement Network Interface Details Collection
- [x] **Status**: Complete
- **Description**: Read per-interface details from /sys/class/net/{iface}/
- **Acceptance Criteria**:
  - [x] Reads MAC address from address file
  - [x] Reads link speed from speed file (handles missing)
  - [x] Reads MTU from mtu file
  - [x] Reads operational state from operstate file
  - [x] Converts is_up from "up"/"down" string to bool
  - [x] Handles FileNotFoundError for optional fields
- **Technical Approach**:
  - Read each file from /sys/class/net/{iface}/
  - Use try/except for optional fields (speed may not exist)
  - Default speed to 0 if unavailable
  - See architecture doc lines 214-234
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/stats_collector.py` - Interface detail collection
- **Dependencies**: Task 3.4
- **Complexity**: M

---

#### Task 3.6: Implement Network IP Address Collection
- [x] **Status**: Complete
- **Description**: Get IP addresses for each interface using psutil
- **Acceptance Criteria**:
  - [x] Uses psutil.net_if_addrs() to get addresses
  - [x] Filters for AF_INET (IPv4) and AF_INET6
  - [x] Excludes link-local IPv6 (fe80::)
  - [x] Returns list of address strings
- **Technical Approach**:
  - Call psutil.net_if_addrs().get(iface, [])
  - Filter by address family
  - Skip fe80:: prefixes
  - See architecture doc lines 236-242
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/stats_collector.py` - IP address collection
- **Dependencies**: Task 3.4
- **Complexity**: S

---

#### Task 3.7: Implement Network Traffic Counters
- [x] **Status**: Complete
- **Description**: Get bytes sent/received from psutil
- **Acceptance Criteria**:
  - [x] Uses psutil.net_io_counters(pernic=True)
  - [x] Gets bytes_sent and bytes_recv for each interface
  - [x] Handles missing counters (default to 0)
- **Technical Approach**:
  - Call psutil.net_io_counters(pernic=True)
  - Look up interface in returned dict
  - Extract bytes_sent and bytes_recv
  - See architecture doc lines 244-247
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/stats_collector.py` - Traffic counters
- **Dependencies**: Task 3.4
- **Complexity**: S

---

#### Task 3.8: Implement Network Rate Calculation
- [x] **Status**: Complete
- **Description**: Calculate bytes/sec rates from delta between collections
- **Acceptance Criteria**:
  - [x] Stores previous sample in self._prev_net dict
  - [x] Calculates time delta from previous sample
  - [x] Computes bytes_sent_rate and bytes_recv_rate
  - [x] Handles first collection (no previous data)
  - [x] Returns 0.0 rates on first collection or zero time delta
- **Technical Approach**:
  - Maintain self._prev_net = {} in __init__
  - Store time, sent, recv for each interface
  - Calculate delta on next collection
  - rate = (current - previous) / time_delta
  - See architecture doc lines 249-264
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/stats_collector.py` - Rate calculation
- **Dependencies**: Task 3.7
- **Complexity**: M

---

#### Task 3.9: Assemble NetworkInterfaceStats Objects
- [x] **Status**: Complete
- **Description**: Combine all network data into NetworkInterfaceStats instances
- **Acceptance Criteria**:
  - [x] Creates NetworkInterfaceStats for each physical interface
  - [x] All fields populated correctly
  - [x] Returns list of NetworkInterfaceStats
  - [x] Skips interfaces that error during collection
- **Technical Approach**:
  - Combine data from tasks 3.4-3.8
  - Wrap in try/except to skip failed interfaces
  - Append to interfaces list
  - See architecture doc lines 266-281
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/stats_collector.py` - _collect_network() complete
- **Dependencies**: Tasks 2.3, 3.4-3.8
- **Complexity**: M

---

#### Task 3.10: Implement GPU Enumeration
- [x] **Status**: Complete
- **Description**: List all GPUs using pynvml
- **Acceptance Criteria**:
  - [x] Uses pynvml.nvmlDeviceGetCount()
  - [x] Iterates all GPU indices
  - [x] Gets handle for each GPU
  - [x] Returns list of handles and indices
- **Technical Approach**:
  - Loop over range(pynvml.nvmlDeviceGetCount())
  - Get handle via pynvml.nvmlDeviceGetHandleByIndex(i)
  - See architecture doc lines 283-286
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/stats_collector.py` - GPU enumeration in _collect_gpus()
- **Dependencies**: Task 3.1
- **Complexity**: S

---

#### Task 3.11: Implement GPU Basic Info Collection
- [x] **Status**: Complete
- **Description**: Get UUID, chip model, PCI bus ID for each GPU
- **Acceptance Criteria**:
  - [x] Gets UUID via nvmlDeviceGetUUID()
  - [x] Gets chip model via nvmlDeviceGetName()
  - [x] Gets PCI info via nvmlDeviceGetPciInfo()
  - [x] Decodes PCI bus ID from bytes if needed
- **Technical Approach**:
  - Call pynvml functions for each handle
  - Handle bytes decoding for bus ID
  - See architecture doc lines 288-311
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/stats_collector.py` - GPU basic info
- **Dependencies**: Task 3.10
- **Complexity**: S

---

#### Task 3.12: Implement GPU Memory and Utilization Collection
- [x] **Status**: Complete
- **Description**: Get memory and utilization metrics for each GPU
- **Acceptance Criteria**:
  - [x] Gets memory info via nvmlDeviceGetMemoryInfo()
  - [x] Converts bytes to GB for total and used
  - [x] Gets utilization via nvmlDeviceGetUtilizationRates()
  - [x] Gets GPU utilization percent
- **Technical Approach**:
  - Call nvmlDeviceGetMemoryInfo(handle)
  - Convert mem.total and mem.used to GB (/ 1024^3)
  - Call nvmlDeviceGetUtilizationRates(handle)
  - Extract util.gpu
  - See architecture doc lines 293-296
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/stats_collector.py` - GPU metrics
- **Dependencies**: Task 3.10
- **Complexity**: S

---

#### Task 3.13: Implement GPU Temperature and Power Collection
- [x] **Status**: Complete
- **Description**: Get temperature and power metrics for each GPU
- **Acceptance Criteria**:
  - [x] Gets temperature via nvmlDeviceGetTemperature()
  - [x] Gets power draw via nvmlDeviceGetPowerUsage() (mW to W)
  - [x] Gets power limit via nvmlDeviceGetPowerManagementLimit() (mW to W)
  - [x] Handles NVMLError for power (some GPUs don't support)
  - [x] Defaults to 0.0 if power unavailable
- **Technical Approach**:
  - Call nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)
  - Try to get power, catch NVMLError
  - Convert mW to W by dividing by 1000
  - See architecture doc lines 298-307
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/stats_collector.py` - GPU temp/power
- **Dependencies**: Task 3.10
- **Complexity**: M

---

#### Task 3.14: Implement GPU Card Manufacturer Detection
- [x] **Status**: Complete
- **Description**: Determine card manufacturer from PCI subsystem vendor
- **Acceptance Criteria**:
  - [x] Reads /sys/bus/pci/devices/{bus_id}/subsystem_vendor
  - [x] Looks up vendor ID in known manufacturers map
  - [x] Returns manufacturer name (eVGA, MSI, ASUS, etc.)
  - [x] Returns "Unknown ({vendor_id})" for unknown vendors
  - [x] Handles FileNotFoundError gracefully
- **Technical Approach**:
  - Implement _get_card_manufacturer(pci_bus_id)
  - Read subsystem_vendor file from sysfs
  - Maintain vendor ID map (0x3842=eVGA, 0x1462=MSI, etc.)
  - See architecture doc lines 343-388
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/stats_collector.py` - _get_card_manufacturer() and _pci_vendor_lookup()
- **Dependencies**: Task 3.11
- **Complexity**: M

---

#### Task 3.15: Implement GPU Serial Number Collection
- [x] **Status**: Complete
- **Description**: Get GPU serial number if available
- **Acceptance Criteria**:
  - [x] Tries nvmlDeviceGetSerial()
  - [x] Handles NVMLError (not all GPUs have serial)
  - [x] Returns None if unavailable
- **Technical Approach**:
  - Try nvmlDeviceGetSerial(handle)
  - Catch NVMLError, return None
  - See architecture doc lines 317-320
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/stats_collector.py` - Serial collection
- **Dependencies**: Task 3.10
- **Complexity**: S

---

#### Task 3.16: Assemble GPUStats Objects
- [x] **Status**: Complete
- **Description**: Combine all GPU data into GPUStats instances
- **Acceptance Criteria**:
  - [x] Creates GPUStats for each GPU
  - [x] All fields populated correctly
  - [x] chip_manufacturer hardcoded to "NVIDIA" (future-proof for AMD)
  - [x] model_loaded calls _get_model_for_gpu(index) (stub for now)
  - [x] Returns list of GPUStats
- **Technical Approach**:
  - Combine data from tasks 3.10-3.15
  - Create GPUStats instance per GPU
  - model_loaded will be implemented in Section 4
  - See architecture doc lines 325-341
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/stats_collector.py` - _collect_gpus() complete
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/stats_collector.py` - _get_model_for_gpu() stub
- **Dependencies**: Tasks 2.4, 3.10-3.15
- **Complexity**: M

---

## Section 4: ContainerManager Service

**Purpose**: Manage LLM container lifecycle using podman-py

**Progress**: 9/9 tasks (100%)

---

#### Task 4.1: Create ContainerManager Skeleton
- [x] **Status**: Complete
- **Description**: Set up ContainerManager class with Podman client initialization
- **Acceptance Criteria**:
  - [x] Class initializes PodmanClient with socket path
  - [x] Maintains running_containers dict (model_quant -> Container)
  - [x] Basic structure matches architecture doc lines 485-490
- **Technical Approach**:
  - Import PodmanClient from podman
  - Initialize with unix socket URL
  - Create empty dict for tracking containers
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/container_manager.py` - ContainerManager class
- **Dependencies**: None
- **Complexity**: S

---

#### Task 4.2: Implement GPU Device Specification
- [x] **Status**: Complete
- **Description**: Generate nvidia-container-toolkit device specs for Podman
- **Acceptance Criteria**:
  - [x] _build_gpu_devices(gpu_indices) returns list of device strings
  - [x] Format: "nvidia.com/gpu={index}" for each GPU
  - [x] Matches architecture doc lines 522-525
- **Technical Approach**:
  - Simple list comprehension
  - Return [f"nvidia.com/gpu={i}" for i in gpu_indices]
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/container_manager.py` - _build_gpu_devices() method
- **Dependencies**: Task 4.1
- **Complexity**: S

---

#### Task 4.3: Implement Environment Variable Builder
- [x] **Status**: Complete
- **Description**: Build environment dict for LLM container
- **Acceptance Criteria**:
  - [x] Sets CUDA_VISIBLE_DEVICES to GPU indices
  - [x] For vLLM runtime, sets VLLM_WORKER_MULTIPROC_METHOD=spawn
  - [x] Returns dict[str, str]
  - [x] Matches architecture doc lines 527-534
- **Technical Approach**:
  - Create base env with CUDA_VISIBLE_DEVICES
  - Add runtime-specific vars for vLLM
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/container_manager.py` - _build_env() method
- **Dependencies**: Task 4.1
- **Complexity**: S

---

#### Task 4.4: Implement vLLM Command Builder
- [x] **Status**: Complete
- **Description**: Generate vLLM command line arguments
- **Acceptance Criteria**:
  - [x] Returns list of command arguments
  - [x] Includes: --model, --max-model-len, --tensor-parallel-size, --pipeline-parallel-size, --max-num-seqs, --host, --port
  - [x] Model path prefixed with /models/
  - [x] Host set to 0.0.0.0, port to 8000
  - [x] Matches architecture doc lines 536-547
- **Technical Approach**:
  - Build list of strings with vLLM flags
  - Use ContainerConfig fields for values
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/container_manager.py` - _build_command() for vLLM
- **Dependencies**: Task 4.1
- **Complexity**: M

---

#### Task 4.5: Implement SGLang Command Builder
- [x] **Status**: Complete
- **Description**: Generate SGLang command line arguments
- **Acceptance Criteria**:
  - [x] Returns list of command arguments for SGLang
  - [x] Includes: --model-path, --context-length, --tp, --host, --port
  - [x] Matches architecture doc lines 548-555
- **Technical Approach**:
  - Similar to vLLM but different flags
  - Use SGLang-specific argument names
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/container_manager.py` - _build_command() for SGLang
- **Dependencies**: Task 4.1
- **Complexity**: M

---

#### Task 4.6: Implement Container Start Logic
- [x] **Status**: Complete
- **Description**: Start an LLM container with specified configuration
- **Acceptance Criteria**:
  - [x] Generates unique container name (llm-{model_quant}-{random})
  - [x] Calls client.containers.run() with correct args
  - [x] Sets detach=True, remove=False
  - [x] Uses dynamic port mapping (8000/tcp: None)
  - [x] Mounts model path read-only
  - [x] Sets labels: llm-serve=true, model, runtime, gpus (JSON)
  - [x] Sets shm_size to 16g
  - [x] Stores container in running_containers dict
  - [x] Returns container ID
  - [x] Matches architecture doc lines 492-520
- **Technical Approach**:
  - Build all arguments using helper methods
  - Call PodmanClient.containers.run()
  - Store reference keyed by model_quant
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/container_manager.py` - start_container() method
- **Dependencies**: Tasks 2.7, 4.1-4.5
- **Complexity**: L

---

#### Task 4.7: Implement Container Stop Logic
- [x] **Status**: Complete
- **Description**: Stop and remove a running container
- **Acceptance Criteria**:
  - [x] Looks up container by model_quant
  - [x] Returns early if not running
  - [x] Calls container.stop(timeout=30)
  - [x] Calls container.remove()
  - [x] Removes from running_containers dict
  - [x] Accepts evicting parameter (for future use)
  - [x] Matches architecture doc lines 559-567
- **Technical Approach**:
  - Check if model_quant in running_containers
  - Stop with 30s grace period
  - Remove container
  - Delete from dict
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/container_manager.py` - stop_container() method
- **Dependencies**: Task 4.1
- **Complexity**: M

---

#### Task 4.8: Implement Container Port Lookup
- [x] **Status**: Complete
- **Description**: Get the host port mapped to container's port 8000
- **Acceptance Criteria**:
  - [x] Looks up container by model_quant
  - [x] Returns None if container not found
  - [x] Gets port mapping from container.ports
  - [x] Extracts HostPort from mapping
  - [x] Returns int port number
  - [x] Matches architecture doc lines 569-577
- **Technical Approach**:
  - Access container.ports dict
  - Look up "8000/tcp" key
  - Extract HostPort from first mapping
  - Return as int
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/container_manager.py` - get_container_port() method
- **Dependencies**: Task 4.1
- **Complexity**: S

---

#### Task 4.9: Implement Container Stats Collection
- [x] **Status**: Complete
- **Description**: Collect stats for all running LLM containers
- **Acceptance Criteria**:
  - [x] Lists all containers via podman.containers.list()
  - [x] Filters for containers with label llm-serve=true
  - [x] Extracts container ID (first 12 chars)
  - [x] Reads labels: model, runtime, gpus (JSON decode)
  - [x] Gets status and calculates uptime
  - [x] Returns list of ContainerStats
  - [x] Used by StatsCollector._collect_containers()
  - [x] Matches architecture doc lines 390-403
- **Technical Approach**:
  - Call self.client.containers.list()
  - Filter by labels.get("llm-serve") == "true"
  - Build ContainerStats from each
  - Parse gpus label as JSON
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/container_manager.py` - get_running_containers() method
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/stats_collector.py` - _collect_containers() implementation
- **Dependencies**: Tasks 2.5, 4.1
- **Complexity**: M

---

## Section 5: HealthMonitor Service

**Purpose**: Monitor container health and auto-restart crashed containers

**Progress**: 6/6 tasks (100%)

---

#### Task 5.1: Create HealthMonitor Skeleton
- [x] **Status**: Complete
- **Description**: Set up HealthMonitor class with initialization
- **Acceptance Criteria**:
  - [x] Class accepts ContainerManager and WebSocketClient in __init__ (WebSocketClient will be stub for now)
  - [x] Sets health_check_interval from config (5 seconds)
  - [x] Initializes containers_starting and containers_evicting sets
  - [x] Matches architecture doc lines 606-618
- **Technical Approach**:
  - Store references to container_manager
  - Create empty sets for state tracking
  - Accept websocket_client but don't use yet (Phase 4)
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/health_monitor.py` - HealthMonitor class
- **Dependencies**: None
- **Complexity**: S

---

#### Task 5.2: Implement Health Check Loop
- [x] **Status**: Complete
- **Description**: Main async loop that checks all containers periodically
- **Acceptance Criteria**:
  - [x] Runs continuously in async loop
  - [x] Calls check_all_containers() every health_check_interval seconds
  - [x] Never exits (until cancelled)
  - [x] Matches architecture doc lines 620-624
- **Technical Approach**:
  - while True loop
  - await self.check_all_containers()
  - await asyncio.sleep(self.health_check_interval)
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/health_monitor.py` - run() method
- **Dependencies**: Task 5.1
- **Complexity**: S

---

#### Task 5.3: Implement Container Health Checking
- [x] **Status**: Complete
- **Description**: Check health of a single container
- **Acceptance Criteria**:
  - [x] Reloads container status from Podman
  - [x] Returns "crashed" if status != "running"
  - [x] For containers older than 30s, checks HTTP /health endpoint
  - [x] Returns "healthy" if HTTP 200 response
  - [x] Returns "unhealthy" if HTTP fails
  - [x] Returns "starting" for new containers (<30s old)
  - [x] Uses httpx.AsyncClient for HTTP check
  - [x] 5 second timeout on health check
  - [x] Matches architecture doc lines 641-664
- **Technical Approach**:
  - Call container.reload() to update status
  - Check container.status
  - Calculate container age
  - If old enough, HTTP GET to http://localhost:{port}/health
  - Handle exceptions as unhealthy
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/health_monitor.py` - check_container_health() method
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/health_monitor.py` - _container_age_seconds() helper
- **Dependencies**: Task 5.1
- **Complexity**: M

---

#### Task 5.4: Implement All Containers Check
- [x] **Status**: Complete
- **Description**: Iterate all running containers and check health
- **Acceptance Criteria**:
  - [x] Iterates container_manager.running_containers
  - [x] Skips containers in containers_evicting set
  - [x] Calls check_container_health() for each
  - [x] Calls handle_crash() if status is "crashed"
  - [x] Matches architecture doc lines 626-639
- **Technical Approach**:
  - Loop over running_containers.items()
  - Skip if in evicting set
  - Check health, handle crashes
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/health_monitor.py` - check_all_containers() method
- **Dependencies**: Tasks 5.1, 5.3
- **Complexity**: M

---

#### Task 5.5: Implement Crash Handler
- [x] **Status**: Complete
- **Description**: Handle crashed container by logging and marking for restart
- **Acceptance Criteria**:
  - [x] Logs warning with model_quant and container_id
  - [x] For Phase 2, just logs (WebSocket notification in Phase 4)
  - [x] Retrieves stored ContainerConfig (stub for now)
  - [x] Removes crashed container forcefully
  - [x] Restarts container with same config
  - [x] Logs success after restart
  - [x] Matches architecture doc lines 666-692
- **Technical Approach**:
  - Log crash event
  - container.remove(force=True)
  - For Phase 2, config retrieval is stub (return None)
  - Full implementation in Phase 4 with Dashboard
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/health_monitor.py` - handle_crash() method
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/health_monitor.py` - _get_stored_config() stub
- **Dependencies**: Task 5.1
- **Complexity**: M

---

#### Task 5.6: Implement Eviction Marking
- [x] **Status**: Complete
- **Description**: Mark containers as being evicted to prevent auto-restart
- **Acceptance Criteria**:
  - [x] mark_evicting(model_quant) adds to containers_evicting set
  - [x] unmark_evicting(model_quant) removes from set
  - [x] Used by ContainerManager when stopping for eviction
  - [x] Matches architecture doc lines 694-700
- **Technical Approach**:
  - Simple set operations
  - Add/discard from containers_evicting
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/health_monitor.py` - mark_evicting() and unmark_evicting() methods
- **Dependencies**: Task 5.1
- **Complexity**: S

---

## Section 6: Main Entrypoint

**Purpose**: Wire up all components and start daemon services

**Progress**: 5/5 tasks (100%)

---

#### Task 6.1: Create Main Module Structure
- [x] **Status**: Complete
- **Description**: Set up main.py with imports and global service instances
- **Acceptance Criteria**:
  - [x] Imports all services and config
  - [x] Loads config from environment
  - [x] Initializes stats_collector, container_manager
  - [x] Creates health_monitor with stub websocket_client
  - [x] Matches architecture doc lines 936-951
- **Technical Approach**:
  - Import Config, StatsCollector, ContainerManager, HealthMonitor
  - Create global instances
  - WebSocketClient initialization is stub for Phase 2 (implemented in Phase 4)
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/main.py` - Imports and initialization
- **Dependencies**: Tasks 1.1, 3.1, 4.1, 5.1
- **Complexity**: S

---

#### Task 6.2: Implement Stats Collection Loop
- [x] **Status**: Complete
- **Description**: Periodic stats collection and output
- **Acceptance Criteria**:
  - [x] Runs in async loop every STATS_INTERVAL_SECONDS
  - [x] Calls stats_collector.collect()
  - [x] For Phase 2, prints stats to stdout (JSON)
  - [x] In Phase 4, will send via WebSocket
  - [x] Never exits
  - [x] Matches architecture doc lines 953-959
- **Technical Approach**:
  - while True loop
  - await stats_collector.collect()
  - Print JSON to stdout for now
  - await asyncio.sleep(config.stats_interval_seconds)
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/main.py` - stats_loop() function
- **Dependencies**: Tasks 3.1, 6.1
- **Complexity**: S

---

#### Task 6.3: Implement Main Entrypoint
- [x] **Status**: Complete
- **Description**: Main async function that starts all background tasks
- **Acceptance Criteria**:
  - [x] Logs daemon startup with machine_id
  - [x] Creates background task for health_monitor.run()
  - [x] Creates background task for stats_loop()
  - [x] For Phase 2, runs indefinitely (no WebSocket connection)
  - [x] In Phase 4, will await websocket_client.connect()
  - [x] Matches architecture doc lines 961-970
- **Technical Approach**:
  - asyncio.create_task() for background tasks
  - Keep main coroutine alive with await asyncio.Event().wait()
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/main.py` - main() function
- **Dependencies**: Tasks 5.2, 6.1, 6.2
- **Complexity**: M

---

#### Task 6.4: Add Command Line Entrypoint
- [x] **Status**: Complete
- **Description**: Make module executable with python -m
- **Acceptance Criteria**:
  - [x] if __name__ == "__main__": asyncio.run(main())
  - [x] Can run with python -m src.main
  - [x] Matches architecture doc lines 972-973
- **Technical Approach**:
  - Add standard Python module guard
  - Call asyncio.run(main())
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/main.py` - Module guard
- **Dependencies**: Task 6.3
- **Complexity**: S

---

#### Task 6.5: Test Daemon Startup and Stats Output
- [x] **Status**: Complete
- **Description**: Validate daemon starts and collects stats
- **Acceptance Criteria**:
  - [x] Daemon container starts without errors
  - [x] Stats printed to stdout every 6 seconds
  - [x] Stats JSON matches architecture example
  - [x] All stats fields populated (CPU, memory, network, GPU)
  - [x] No crashes or exceptions in logs
- **Technical Approach**:
  - Build and run daemon container
  - Mount /proc, /sys, podman socket, GPU access
  - Observe stdout for stats output
  - Validate JSON structure against architecture doc example
- **Files/Components**:
  - [x] All daemon source files
  - [x] `/data/home/mgreger/proj/llms/daemon/Containerfile`
- **Dependencies**: All previous tasks
- **Complexity**: L

---

## Testing Strategy

### Unit Testing
- **Not required for Phase 2**: Focus on manual validation
- **Future**: Add tests for critical parsing logic (CPU info, memory info)

### Integration Testing
- **Manual testing**:
  1. Build daemon container
  2. Run with host mounts and GPU access
  3. Observe stats output
  4. Verify all fields present
  5. Test container start/stop via manual commands
  6. Verify health monitoring detects crashes

### Validation Criteria
- [x] Stats output matches architecture doc example (PRD Appendix B)
- [x] All GPU fields populated correctly
- [x] Network interfaces detected and rates calculated
- [x] CPU manufacturer and model extracted correctly
- [x] Memory values in GB are accurate
- [x] Container stats include running LLM containers

---

## Dependencies

### External Libraries
```toml
# pyproject.toml
[project]
dependencies = [
    "pynvml>=11.5",
    "psutil>=5.9",
    "podman-py>=4.8",
    "structlog>=23.2",
    "pydantic>=2.5",
    "httpx>=0.25",
]
```

### System Requirements
- Host must have:
  - nvidia-container-toolkit installed
  - Podman socket enabled
  - /proc and /sys accessible
  - NFS model path mounted (for container starts)

---

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| pynvml can't access GPUs from container | High | Medium | Test --device nvidia.com/gpu=all flag early |
| Podman socket permissions | High | Medium | Document user vs system socket configuration |
| /proc parsing varies by kernel version | Medium | Low | Test on Fedora 38-43, handle missing fields |
| PCI vendor lookup incomplete | Low | Medium | Default to "Unknown" for unmapped vendors |
| Container stats empty on first run | Low | Medium | Handle empty container list gracefully |

---

## Exit Criteria Checklist

- [x] All 47 tasks completed
- [x] Daemon container builds successfully
- [x] Daemon collects all stats (CPU, memory, network, GPU)
- [x] Stats JSON matches architecture schema
- [x] Container start/stop works via ContainerManager
- [x] Health monitoring detects crashed containers
- [x] Environment variable configuration works
- [ ] Code committed to repository
- [ ] Manual testing confirms all functionality

---

## Next Phase

**Phase 3**: Dashboard Backend
- Build FastAPI application structure
- Create TimescaleDB schema
- Implement Control API endpoints
- Set up database migrations
