# Container Command Generator Service - Phase 7

## Overview

Created the `ContainerCommandGenerator` service and `PortAllocator` utility for generating podman run commands to start LLM inference containers.

## Files Created

### 1. `/data/home/mgreger/proj/llms/dashboard/backend/services/container_command.py`

Main service implementation with two classes:

#### PortAllocator Class
Thread-safe port allocation for container services.

**Features:**
- Manages ports in range 8001-8999 (configurable)
- Uses `asyncio.Lock` for thread safety
- Methods:
  - `allocate() -> int`: Allocate next available port
  - `release(port: int)`: Free a previously allocated port
  - `get_allocated() -> set[int]`: Get all allocated ports

**Example:**
```python
allocator = PortAllocator(min_port=8001, max_port=8999)
port = await allocator.allocate()  # Returns 8001 (first available)
await allocator.release(port)       # Free it for reuse
```

#### ContainerCommandGenerator Class
Generates podman run commands for LLM inference containers.

**Initialization:**
```python
generator = ContainerCommandGenerator(
    port_allocator=None,  # Optional, creates new if None
    model_path=None       # Optional, uses settings.model_path if None
)
```

**Main Method:**
```python
cmd = await generator.generate(
    config: ContainerConfig,
    model_quant: ModelQuantization,
    model: Model,
    gpus: list[int],
    port: Optional[int] = None  # Auto-allocates if None
) -> list[str]
```

**Runtime Support:**
- `vllm`: Fully implemented with complete command generation
- `sglang`: Stub that raises `NotImplementedError`
- `llamacpp`: Stub that raises `NotImplementedError`
- Unknown runtimes raise `ValueError`

### 2. `/data/home/mgreger/proj/llms/dashboard/backend/tests/test_container_command.py`

Comprehensive test suite with 20 test cases covering:

#### PortAllocator Tests
- Single port allocation
- Multiple unique port allocations
- Port release and reallocation
- Port exhaustion error handling
- Thread-safe concurrent allocation

#### ContainerCommandGenerator Tests
- vLLM single GPU command generation
- vLLM multi-GPU command generation
- GPU device formatting
- Environment variable building
- Container label generation
- Container name generation with random suffix
- Extra vLLM arguments from config
- Custom container image support
- Automatic port allocation
- Pipeline parallel configuration
- Model without file_path fallback
- SGLang NotImplementedError
- llama.cpp NotImplementedError
- Unknown runtime ValueError

## vLLM Command Structure

Generated commands follow this structure:

```bash
podman run -d --rm \
  --name vllm-{model}-{quant}-{random_id} \
  --device nvidia.com/gpu=0 \
  --device nvidia.com/gpu=1 \
  -v /path/to/models:/models:ro \
  --shm-size 16g \
  -p {port}:8000 \
  -e CUDA_VISIBLE_DEVICES=0,1 \
  -e HF_TOKEN=xxx \
  --label llm-serve=true \
  --label model={model-quant} \
  --label runtime=vllm \
  --label gpus=[0,1] \
  vllm/vllm-openai:latest \
  --model /models/{model_path} \
  --max-model-len 8192 \
  --tensor-parallel-size 2 \
  --pipeline-parallel-size 1 \
  --max-num-seqs 4
```

## Key Features

### 1. GPU Management
- Multiple GPU support via `--device nvidia.com/gpu=N`
- CUDA_VISIBLE_DEVICES environment variable
- GPU list stored in container labels as JSON

### 2. Volume Mounting
- Models mounted read-only: `-v {MODEL_PATH}:/models:ro`
- Uses `model_quant.file_path` if available
- Falls back to `model.name` if no file_path

### 3. Port Allocation
- Thread-safe allocation from port pool (8001-8999)
- Automatic allocation if port not specified
- Prevents port conflicts

### 4. Container Configuration
- Shared memory: `--shm-size 16g` (required for vLLM)
- Detached mode: `-d`
- Auto-remove: `--rm`
- Unique container names with random 8-char suffix

### 5. Labels for Management
- `llm-serve=true`: Identifies our containers
- `model={name}-{quant}`: Model identifier
- `runtime={vllm|sglang|llamacpp}`: Runtime engine
- `gpus=[0,1,2]`: GPU allocation as JSON array

### 6. vLLM-Specific Arguments
- `--model`: Path to model in container
- `--max-model-len`: Context window size
- `--tensor-parallel-size`: Number of GPUs for tensor parallelism
- `--pipeline-parallel-size`: Pipeline parallelism (if > 1)
- `--max-num-seqs`: Maximum parallel requests
- Extra args from `config.extra_args["vllm_args"]`

### 7. Custom Configuration
- Custom container image via `config.extra_args["image"]`
- Additional environment variables in `config.extra_args`
- Extra vLLM arguments via `config.extra_args["vllm_args"]`

## Helper Methods

### _format_gpu_devices(gpus: list[int]) -> list[str]
Converts GPU indices to podman device arguments:
```python
[0, 2, 4] → ["--device", "nvidia.com/gpu=0", "--device", "nvidia.com/gpu=2", "--device", "nvidia.com/gpu=4"]
```

### _build_env_args(config_env: dict, gpus: list[int]) -> list[str]
Builds environment variable arguments:
```python
{{"HF_TOKEN": "xxx"}, [0, 1]} → ["-e", "CUDA_VISIBLE_DEVICES=0,1", "-e", "HF_TOKEN=xxx"]
```

### _build_label_args(model_quant: str, runtime: str, gpus: list[int]) -> list[str]
Generates container labels:
```python
("qwen2.5-7b-awq", "vllm", [0]) → ["--label", "llm-serve=true", "--label", "model=qwen2.5-7b-awq", ...]
```

### _container_name(model_name: str, quant: str) -> str
Creates unique container name:
```python
("qwen2.5-72b-instruct", "awq") → "vllm-qwen2-5-72b-instruct-awq-a1b2c3d4"
```

## Integration Points

### With Database Models
- `ContainerConfig`: Runtime settings, parallelism, context length
- `ModelQuantization`: Model files, VRAM requirements, GPU count
- `Model`: Base model name and metadata

### With Configuration
- Uses `settings.model_path` from `/data/home/mgreger/proj/llms/dashboard/backend/config.py`
- Configurable via `MODEL_PATH` environment variable

### With Services
- Exported from `dashboard.backend.services.__init__.py`
- Ready for use by container orchestration services

## Usage Example

```python
from dashboard.backend.services import ContainerCommandGenerator, PortAllocator
from dashboard.backend.models.database import ContainerConfig, Model, ModelQuantization

# Initialize
allocator = PortAllocator()
generator = ContainerCommandGenerator(port_allocator=allocator)

# Create database objects (normally from DB queries)
model = Model(name="qwen2.5-7b-instruct", ...)
quant = ModelQuantization(quantization="awq", file_path="qwen2.5-7b-awq", ...)
config = ContainerConfig(
    runtime="vllm",
    context_length=8192,
    tensor_parallel=2,
    max_parallel=4,
    ...
)

# Generate command
cmd = await generator.generate(
    config=config,
    model_quant=quant,
    model=model,
    gpus=[0, 1],  # Use GPUs 0 and 1
    port=None     # Auto-allocate port
)

# cmd is now a list ready for subprocess.run()
# Example: ["podman", "run", "-d", "--rm", "--name", "vllm-...", ...]
```

## Future Enhancements

When implementing SGLang and llama.cpp support:

1. Implement `_generate_sglang()`:
   - Similar structure to vLLM
   - Different image: `lmsysorg/sglang:latest`
   - SGLang-specific arguments

2. Implement `_generate_llamacpp()`:
   - Image: `ghcr.io/ggerganov/llama.cpp:server`
   - CPU-based by default
   - Different argument format

3. Add runtime-specific validation:
   - Check quantization compatibility
   - Validate GPU count requirements

## Testing

Run tests with:
```bash
python -m pytest dashboard/backend/tests/test_container_command.py -v
```

Or use the verification script:
```bash
python verify_container_command.py
```

## Error Handling

- `ValueError`: Unknown runtime specified
- `NotImplementedError`: Runtime not yet implemented (sglang, llamacpp)
- `RuntimeError`: Port pool exhausted (no available ports)
