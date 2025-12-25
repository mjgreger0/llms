# Container Command Generator - Architecture

## Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Container Orchestration                   │
│                   (Future Phase 7 Service)                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Uses
                     ▼
┌─────────────────────────────────────────────────────────────┐
│          ContainerCommandGenerator (Service)                 │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ generate(config, model_quant, model, gpus, port?)    │   │
│  └───┬──────────────────────────────────────────────────┘   │
│      │                                                       │
│      ├─► Runtime Dispatch                                   │
│      │   ├─► _generate_vllm()      [IMPLEMENTED]            │
│      │   ├─► _generate_sglang()    [STUB]                   │
│      │   └─► _generate_llamacpp()  [STUB]                   │
│      │                                                       │
│      └─► Helper Methods                                     │
│          ├─► _format_gpu_devices()                          │
│          ├─► _build_env_args()                              │
│          ├─► _build_label_args()                            │
│          └─► _container_name()                              │
│                                                              │
└────────────┬──────────────────────────────┬─────────────────┘
             │                              │
             │ Uses                         │ Uses
             ▼                              ▼
┌─────────────────────────┐    ┌──────────────────────────────┐
│    PortAllocator        │    │   Database Models            │
│                         │    │                              │
│  ┌───────────────────┐  │    │  ┌────────────────────────┐  │
│  │ allocate() → int  │  │    │  │ ContainerConfig        │  │
│  │ release(port)     │  │    │  │  - runtime             │  │
│  │ get_allocated()   │  │    │  │  - context_length      │  │
│  └───────────────────┘  │    │  │  - tensor_parallel     │  │
│                         │    │  │  - max_parallel        │  │
│  Thread-safe with       │    │  │  - extra_args          │  │
│  asyncio.Lock           │    │  └────────────────────────┘  │
│                         │    │                              │
│  Port Range: 8001-8999  │    │  ┌────────────────────────┐  │
└─────────────────────────┘    │  │ ModelQuantization      │  │
                               │  │  - quantization        │  │
                               │  │  - file_path           │  │
                               │  │  - vram_required_gb    │  │
                               │  └────────────────────────┘  │
                               │                              │
                               │  ┌────────────────────────┐  │
                               │  │ Model                  │  │
                               │  │  - name                │  │
                               │  │  - provider            │  │
                               │  └────────────────────────┘  │
                               └──────────────────────────────┘
```

## Data Flow - vLLM Command Generation

```
Input:
  config: ContainerConfig
  model_quant: ModelQuantization
  model: Model
  gpus: [0, 1]
  port: 8001

        │
        ▼
┌────────────────────────────────────────┐
│ 1. Build Base Command                  │
│    ["podman", "run", "-d", "--rm"]     │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│ 2. Generate Container Name             │
│    _container_name()                   │
│    → "vllm-qwen2-5-7b-awq-a1b2c3d4"   │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│ 3. Add GPU Devices                     │
│    _format_gpu_devices([0, 1])         │
│    → ["--device", "nvidia.com/gpu=0",  │
│       "--device", "nvidia.com/gpu=1"]  │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│ 4. Add Volume Mount                    │
│    -v {model_path}:/models:ro          │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│ 5. Add SHM Size                        │
│    --shm-size 16g                      │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│ 6. Add Port Mapping                    │
│    -p 8001:8000                        │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│ 7. Add Environment Variables           │
│    _build_env_args(extra_env, [0, 1])  │
│    → ["-e", "CUDA_VISIBLE_DEVICES=0,1",│
│        "-e", "HF_TOKEN=xxx"]           │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│ 8. Add Container Labels                │
│    _build_label_args(...)              │
│    → ["--label", "llm-serve=true",     │
│        "--label", "model=...",         │
│        "--label", "runtime=vllm",      │
│        "--label", "gpus=[0,1]"]        │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│ 9. Add Container Image                 │
│    vllm/vllm-openai:latest             │
│    (or custom from config)             │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│ 10. Add vLLM Runtime Arguments         │
│     --model /models/{path}             │
│     --max-model-len {context}          │
│     --tensor-parallel-size 2           │
│     --max-num-seqs {parallel}          │
│     + extra args from config           │
└────────────────┬───────────────────────┘
                 │
                 ▼
Output:
  Complete command as list[str]
  Ready for subprocess.run()
```

## Port Allocation Flow

```
┌──────────────────────────────────────────┐
│  Container Orchestration Service         │
│  Needs to start a new container          │
└─────────────────┬────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────────┐
│  PortAllocator.allocate()                │
│                                          │
│  async with self._lock:                  │
│    ┌──────────────────────────────────┐  │
│    │ Scan range 8001-8999             │  │
│    │ Find first unallocated port      │  │
│    │ Add to self._allocated set       │  │
│    │ Return port number                │  │
│    └──────────────────────────────────┘  │
└─────────────────┬────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────────┐
│  Pass port to generate()                 │
│  Create container with allocated port    │
└─────────────────┬────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────────┐
│  Container Running                       │
│  Port in use                             │
└─────────────────┬────────────────────────┘
                  │
                  │ Later: Container stops
                  ▼
┌──────────────────────────────────────────┐
│  PortAllocator.release(port)             │
│                                          │
│  async with self._lock:                  │
│    ┌──────────────────────────────────┐  │
│    │ Remove from self._allocated set │  │
│    │ Port available for reuse         │  │
│    └──────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

## Runtime Dispatch

```
ContainerCommandGenerator.generate()
        │
        ▼
    Check runtime type
        │
        ├─► runtime == "vllm"
        │   └─► _generate_vllm()
        │       └─► Build complete podman command
        │           └─► Return list[str]
        │
        ├─► runtime == "sglang"
        │   └─► _generate_sglang()
        │       └─► raise NotImplementedError
        │
        ├─► runtime == "llamacpp"
        │   └─► _generate_llamacpp()
        │       └─► raise NotImplementedError
        │
        └─► unknown runtime
            └─► raise ValueError("Unknown runtime: {runtime}")
```

## Label System for Container Management

Labels are attached to every container for discovery and management:

```
Container Labels:
┌────────────────────────────────────────────────┐
│ llm-serve=true                                 │  ← Identifies our containers
│ model=qwen2.5-7b-instruct-awq                 │  ← Model identifier
│ runtime=vllm                                  │  ← Runtime engine
│ gpus=[0,1]                                    │  ← GPU allocation (JSON)
└────────────────────────────────────────────────┘

Usage:
  # List all LLM serve containers
  podman ps --filter label=llm-serve=true

  # Find containers for specific model
  podman ps --filter label=model=qwen2.5-7b-instruct-awq

  # Find all vLLM containers
  podman ps --filter label=runtime=vllm

  # Get GPU allocation from labels
  podman inspect container_name | jq '.[0].Config.Labels.gpus'
  → [0,1]
```

## Configuration Extension Points

The service supports customization through `ContainerConfig.extra_args`:

```
ContainerConfig.extra_args = {
  # Custom container image
  "image": "custom/vllm:v0.2.7",

  # Additional environment variables
  "HF_TOKEN": "hf_yourtoken",
  "TRANSFORMERS_CACHE": "/models/.cache",

  # Extra vLLM runtime arguments
  "vllm_args": [
    "--trust-remote-code",
    "--enable-chunked-prefill",
    "--max-num-batched-tokens", "8192"
  ]
}

Result:
  - Custom image used instead of default
  - Environment variables added to container
  - Extra vLLM args appended to command
```

## GPU Management Strategy

```
Physical GPUs:     [GPU0] [GPU1] [GPU2] [GPU3]
                      │     │      │      │
Container Request:    │     │      │      │
  gpus = [0, 2]      │     │      │      │
                     │     │      │      │
                     ▼            ▼
Generated Command:
  --device nvidia.com/gpu=0
  --device nvidia.com/gpu=2
  -e CUDA_VISIBLE_DEVICES=0,2

Inside Container:
  GPU 0 → Physical GPU 0
  GPU 2 → Physical GPU 2
  (GPUs 1, 3 not visible to container)
```

## Thread Safety Guarantees

```
PortAllocator uses asyncio.Lock:

Concurrent Request A          Concurrent Request B
        │                              │
        ▼                              ▼
   allocate()                     allocate()
        │                              │
        ▼                              │
   acquire lock                        │
        │                              │ waiting...
   scan ports                          │
   find 8001                           │
   add to set                          │
   release lock                        │
        │                              ▼
   return 8001                    acquire lock
                                       │
                                  scan ports
                                  find 8002 (8001 taken)
                                  add to set
                                  release lock
                                       │
                                  return 8002

Result: No race conditions, unique ports guaranteed
```

## Integration with Future Components

```
┌──────────────────────────────────────────────┐
│         Container Orchestration              │
│                                              │
│  Start Container:                            │
│  1. Query DB for ContainerConfig             │
│  2. Allocate GPUs from ClusterState          │
│  3. Allocate port from PortAllocator         │
│  4. Generate command                         │
│  5. Execute podman command                   │
│  6. Track container in ClusterState          │
│                                              │
│  Stop Container:                             │
│  1. Execute podman stop                      │
│  2. Release port to PortAllocator            │
│  3. Release GPUs in ClusterState             │
│  4. Update container status in DB            │
└──────────────────────────────────────────────┘
```

## Error Handling Strategy

```
Error Type                     Handling
──────────────────────────────────────────────
Unknown Runtime                ValueError
  → User configuration error
  → Return 400 Bad Request

Runtime Not Implemented        NotImplementedError
  → Feature not available yet
  → Return 501 Not Implemented

Port Pool Exhausted            RuntimeError
  → Resource unavailable
  → Return 503 Service Unavailable
  → Retry after container cleanup

Invalid Configuration          ValueError
  → Data validation error
  → Return 400 Bad Request
```
