# Container Library - Architecture Document

## Document Information
- **Related PRD**: [llms-prd.md](./llms-prd.md)
- **Component**: Container Library
- **Created**: 2025-12-23
- **Status**: Draft
- **Version**: 1.0

---

## Overview

The Container Library provides curated, tested container configurations for running LLM inference. Rather than static container images, the library defines **configurations** that the Dashboard uses to generate `podman run` commands at runtime.

This approach allows:
- Flexible model/quantization combinations without rebuilding containers
- Runtime parameter adjustment (context length, parallelism)
- Use of upstream container images (vLLM, SGLang) without modification
- Easy addition of new models without container changes

---

## High-Level Design

### Responsibilities

- Define runtime requirements for each model+quantization combination
- Specify container images and versions for each inference runtime
- Provide tested default configurations (context length, parallelism)
- Document GPU memory requirements for capacity planning
- Support multi-GPU and multi-machine configurations

### Boundaries

**Owns:**
- Container configuration specifications
- GPU memory requirement data
- Runtime-specific command-line arguments
- Default tuning parameters

**Does NOT own:**
- Container images (uses upstream images)
- Model files (stored on NFS)
- Container lifecycle (Daemon responsibility)
- Routing decisions (Dashboard responsibility)

### Key Abstractions

| Concept | Description |
|---------|-------------|
| **Runtime** | Inference engine: vLLM, SGLang, or llama.cpp |
| **Container Image** | Docker/OCI image for a runtime (e.g., `vllm/vllm-openai:v0.6.0`) |
| **Model Config** | Base model requirements (architecture, size) |
| **Quant Config** | Quantization-specific requirements (VRAM, format) |
| **Launch Config** | Complete configuration to run a model+quant |

---

## Supported Runtimes

### Runtime Priority Order

1. **vLLM** (preferred) - Best performance, widest model support, active development
2. **SGLang** - Alternative when vLLM doesn't support a model, comparable performance
3. **llama.cpp** - For GGUF models only, CPU fallback capability

### Runtime Comparison

| Feature | vLLM | SGLang | llama.cpp |
|---------|------|--------|-----------|
| Model format | Transformers, AWQ, GPTQ | Transformers, AWQ | GGUF only |
| Tensor parallelism | Yes | Yes | Limited |
| Pipeline parallelism | Yes | No | No |
| Continuous batching | Yes | Yes | Limited |
| OpenAI API compatible | Yes | Yes | Yes |
| Vision models | Yes | Yes | Limited |
| Quantizations | AWQ, GPTQ, FP8 | AWQ, FP8 | Q4, Q5, Q6, Q8 |

### Container Images

```yaml
runtimes:
  vllm:
    image: vllm/vllm-openai
    versions:
      stable: v0.6.6
      latest: latest
    health_endpoint: /health
    api_base: /v1

  sglang:
    image: lmsysorg/sglang
    versions:
      stable: v0.3.6
      latest: latest
    health_endpoint: /health
    api_base: /v1

  llamacpp:
    image: ghcr.io/ggerganov/llama.cpp
    versions:
      stable: server
      latest: server
    health_endpoint: /health
    api_base: /v1
```

---

## Configuration Schema

### Database Tables

Container configurations are stored in the Dashboard's TimescaleDB database.

```sql
-- Model configurations (base model info)
CREATE TABLE model_configs (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,   -- e.g., "qwen2.5-72b-instruct"
    family          TEXT,                    -- e.g., "Qwen2.5"
    architecture    TEXT,                    -- e.g., "Qwen2ForCausalLM"
    parameter_count TEXT,                    -- e.g., "72B"
    huggingface_id  TEXT,                    -- e.g., "Qwen/Qwen2.5-72B-Instruct"
    supports_vision BOOLEAN DEFAULT FALSE,
    max_context     INTEGER,                 -- Max context length model supports
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Quantization configurations
CREATE TABLE quantization_configs (
    id              SERIAL PRIMARY KEY,
    model_id        INTEGER REFERENCES model_configs(id),
    quantization    TEXT NOT NULL,          -- e.g., "awq", "fp16", "q4_k_m"
    format          TEXT NOT NULL,          -- "transformers", "awq", "gptq", "gguf"
    file_path       TEXT,                   -- Path within NFS models directory
    file_size_gb    REAL,
    vram_required_gb REAL NOT NULL,         -- Minimum VRAM needed
    recommended_runtime TEXT DEFAULT 'vllm',
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(model_id, quantization)
);

-- Launch configurations (how to run a specific model+quant)
CREATE TABLE launch_configs (
    id              SERIAL PRIMARY KEY,
    quant_id        INTEGER REFERENCES quantization_configs(id),
    runtime         TEXT NOT NULL,          -- vllm, sglang, llamacpp
    image_version   TEXT DEFAULT 'stable',
    gpu_count       INTEGER DEFAULT 1,
    tensor_parallel INTEGER DEFAULT 1,
    pipeline_parallel INTEGER DEFAULT 1,
    context_length  INTEGER DEFAULT 8192,
    max_parallel    INTEGER DEFAULT 4,      -- Max concurrent requests
    extra_args      JSONB,                  -- Runtime-specific arguments
    environment     JSONB,                  -- Environment variables
    is_default      BOOLEAN DEFAULT FALSE,  -- Default config for this quant
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### Launch Configuration Examples

#### Single GPU Model (Qwen 32B AWQ)

```json
{
  "model": "qwen2.5-32b-instruct",
  "quantization": "awq",
  "runtime": "vllm",
  "image": "vllm/vllm-openai:v0.6.6",
  "gpu_count": 1,
  "vram_required_gb": 20,
  "tensor_parallel": 1,
  "pipeline_parallel": 1,
  "context_length": 32768,
  "max_parallel": 8,
  "extra_args": {
    "--quantization": "awq",
    "--dtype": "auto",
    "--gpu-memory-utilization": "0.95"
  },
  "environment": {
    "VLLM_WORKER_MULTIPROC_METHOD": "spawn"
  }
}
```

#### Multi-GPU Model (Qwen 72B AWQ)

```json
{
  "model": "qwen2.5-72b-instruct",
  "quantization": "awq",
  "runtime": "vllm",
  "image": "vllm/vllm-openai:v0.6.6",
  "gpu_count": 2,
  "vram_required_gb": 42,
  "tensor_parallel": 2,
  "pipeline_parallel": 1,
  "context_length": 32768,
  "max_parallel": 4,
  "extra_args": {
    "--quantization": "awq",
    "--dtype": "auto",
    "--gpu-memory-utilization": "0.95"
  },
  "environment": {
    "VLLM_WORKER_MULTIPROC_METHOD": "spawn",
    "NCCL_DEBUG": "WARN"
  }
}
```

#### Multi-Machine Model (Llama 405B FP8)

```json
{
  "model": "llama3.1-405b-instruct",
  "quantization": "fp8",
  "runtime": "vllm",
  "image": "vllm/vllm-openai:v0.6.6",
  "gpu_count": 8,
  "vram_required_gb": 400,
  "tensor_parallel": 8,
  "pipeline_parallel": 1,
  "multi_machine": true,
  "machines_required": 2,
  "gpus_per_machine": 4,
  "context_length": 16384,
  "max_parallel": 2,
  "extra_args": {
    "--dtype": "auto",
    "--gpu-memory-utilization": "0.95",
    "--distributed-executor-backend": "ray"
  },
  "environment": {
    "VLLM_WORKER_MULTIPROC_METHOD": "spawn",
    "NCCL_DEBUG": "WARN",
    "RAY_DEDUP_LOGS": "0"
  },
  "master_args": {
    "--ray-address": "auto"
  },
  "worker_args": {
    "--ray-address": "${MASTER_IP}:6379"
  }
}
```

#### GGUF Model (llama.cpp)

```json
{
  "model": "llama3.1-8b-instruct",
  "quantization": "q4_k_m",
  "runtime": "llamacpp",
  "image": "ghcr.io/ggerganov/llama.cpp:server",
  "gpu_count": 1,
  "vram_required_gb": 6,
  "context_length": 8192,
  "max_parallel": 4,
  "extra_args": {
    "-ngl": "99",
    "-c": "8192",
    "-np": "4"
  },
  "environment": {}
}
```

---

## Command Generation

The Dashboard generates container commands from configurations.

### Command Generator

```python
class ContainerCommandGenerator:
    """Generates podman run commands from launch configurations."""

    def generate(self, config: LaunchConfig, machine: Machine, gpus: list[int]) -> str:
        """Generate podman run command for a model."""

        if config.runtime == "vllm":
            return self._generate_vllm(config, machine, gpus)
        elif config.runtime == "sglang":
            return self._generate_sglang(config, machine, gpus)
        elif config.runtime == "llamacpp":
            return self._generate_llamacpp(config, machine, gpus)
        else:
            raise ValueError(f"Unknown runtime: {config.runtime}")

    def _generate_vllm(self, config: LaunchConfig, machine: Machine, gpus: list[int]) -> str:
        image = f"{RUNTIMES['vllm']['image']}:{config.image_version}"
        model_path = f"/models/{config.file_path}"

        cmd = [
            "podman", "run", "-d",
            "--name", self._container_name(config),
            "--restart=no",
            "-p", f"{self._next_port()}:8000",
            "--shm-size=16g",
        ]

        # GPU devices
        for gpu in gpus:
            cmd.extend(["--device", f"nvidia.com/gpu={gpu}"])

        # Model volume
        cmd.extend(["-v", f"{MODEL_PATH}:/models:ro"])

        # Environment
        env = {
            "CUDA_VISIBLE_DEVICES": ",".join(str(g) for g in gpus),
            **config.environment
        }
        for key, value in env.items():
            cmd.extend(["-e", f"{key}={value}"])

        # Labels for tracking
        cmd.extend([
            "--label", "llm-serve=true",
            "--label", f"model={config.model_quant}",
            "--label", f"runtime={config.runtime}",
            "--label", f"gpus={json.dumps(gpus)}",
        ])

        # Image
        cmd.append(image)

        # vLLM arguments
        cmd.extend([
            "--model", model_path,
            "--max-model-len", str(config.context_length),
            "--tensor-parallel-size", str(config.tensor_parallel),
            "--max-num-seqs", str(config.max_parallel),
            "--host", "0.0.0.0",
            "--port", "8000",
        ])

        # Extra arguments
        for key, value in (config.extra_args or {}).items():
            cmd.extend([key, str(value)])

        return cmd

    def _container_name(self, config: LaunchConfig) -> str:
        return f"llm-{config.model_quant}-{uuid.uuid4().hex[:8]}"
```

### Generated Command Examples

**Single GPU (Qwen 32B AWQ):**
```bash
podman run -d \
  --name llm-qwen2.5-32b-instruct-awq-a1b2c3d4 \
  --restart=no \
  -p 8001:8000 \
  --shm-size=16g \
  --device nvidia.com/gpu=0 \
  -v /data/projects/ai/models:/models:ro \
  -e CUDA_VISIBLE_DEVICES=0 \
  -e VLLM_WORKER_MULTIPROC_METHOD=spawn \
  --label llm-serve=true \
  --label model=qwen2.5-32b-instruct-awq \
  --label runtime=vllm \
  --label gpus=[0] \
  vllm/vllm-openai:v0.6.6 \
  --model /models/Qwen/Qwen2.5-32B-Instruct-AWQ \
  --max-model-len 32768 \
  --tensor-parallel-size 1 \
  --max-num-seqs 8 \
  --host 0.0.0.0 \
  --port 8000 \
  --quantization awq \
  --dtype auto \
  --gpu-memory-utilization 0.95
```

**Multi-GPU (Qwen 72B AWQ):**
```bash
podman run -d \
  --name llm-qwen2.5-72b-instruct-awq-e5f6g7h8 \
  --restart=no \
  -p 8002:8000 \
  --shm-size=16g \
  --device nvidia.com/gpu=0 \
  --device nvidia.com/gpu=1 \
  -v /data/projects/ai/models:/models:ro \
  -e CUDA_VISIBLE_DEVICES=0,1 \
  -e VLLM_WORKER_MULTIPROC_METHOD=spawn \
  -e NCCL_DEBUG=WARN \
  --label llm-serve=true \
  --label model=qwen2.5-72b-instruct-awq \
  --label runtime=vllm \
  --label gpus=[0,1] \
  vllm/vllm-openai:v0.6.6 \
  --model /models/Qwen/Qwen2.5-72B-Instruct-AWQ \
  --max-model-len 32768 \
  --tensor-parallel-size 2 \
  --max-num-seqs 4 \
  --host 0.0.0.0 \
  --port 8000 \
  --quantization awq \
  --dtype auto \
  --gpu-memory-utilization 0.95
```

---

## GPU Memory Requirements

### VRAM Estimation Formula

Approximate VRAM requirements:

```
VRAM (GB) = (Parameters in Billions) × (Bits per Parameter / 8) × 1.2
```

The 1.2 multiplier accounts for KV cache and runtime overhead.

### Reference Table

| Model | Params | FP16 VRAM | AWQ/GPTQ VRAM | Q4 VRAM |
|-------|--------|-----------|---------------|---------|
| Llama 3.1 8B | 8B | 16 GB | 6 GB | 5 GB |
| Qwen 2.5 14B | 14B | 28 GB | 10 GB | 8 GB |
| Qwen 2.5 32B | 32B | 64 GB | 20 GB | 18 GB |
| Llama 3.1 70B | 70B | 140 GB | 42 GB | 35 GB |
| Qwen 2.5 72B | 72B | 144 GB | 44 GB | 36 GB |
| Llama 3.1 405B | 405B | 810 GB | 210 GB | 180 GB |

### Context Length Impact

KV cache VRAM scales with context length:

```
KV Cache (GB) = (layers × heads × head_dim × 2 × context_length × batch_size × bytes) / 1e9
```

For a 70B model with 32k context:
- FP16 KV cache: ~8 GB additional
- Quantized KV cache: ~2-4 GB additional

---

## Multi-Machine Coordination

### Distributed Inference Architecture

For models spanning multiple machines, vLLM uses Ray for distributed execution.

```
┌─────────────────────────────────────────────────────────────┐
│                        Dashboard                             │
│                                                              │
│  1. Identify machines for distributed inference              │
│  2. Send coordinated start commands                          │
│  3. Wait for all nodes healthy                               │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
┌─────────────────────┐       ┌─────────────────────┐
│   Machine A         │       │   Machine B         │
│   (Master Node)     │       │   (Worker Node)     │
│                     │       │                     │
│   Ray Head          │◄─────►│   Ray Worker        │
│   vLLM Controller   │       │   vLLM Worker       │
│   GPUs 0-3          │       │   GPUs 0-3          │
└─────────────────────┘       └─────────────────────┘
          │                               │
          └───────────────┬───────────────┘
                          │
                    NCCL All-Reduce
                    (Tensor Parallelism)
```

### Startup Sequence

1. **Dashboard** selects machines and GPUs for distributed model
2. **Dashboard** sends `container.start` to Machine A with `role=master`
3. **Daemon A** starts Ray head node and vLLM master container
4. **Dashboard** waits for master to report Ray head address
5. **Dashboard** sends `container.start` to Machine B with `role=worker`, `master_address=<A's IP>`
6. **Daemon B** starts Ray worker and vLLM worker container, joins cluster
7. **Dashboard** polls master node health until model ready
8. **All requests** route to master node only

### Shutdown Sequence

1. **Dashboard** sends `container.stop` to all machines simultaneously
2. **Each Daemon** stops its containers
3. **Daemons** report containers stopped
4. **Dashboard** marks GPUs as free on all machines

---

## Model Discovery and Registration

### Phase 1: Manual Registration

In Phase 1, models are registered manually after download:

```sql
-- Add a new model
INSERT INTO model_configs (name, family, huggingface_id, parameter_count, max_context)
VALUES ('qwen2.5-32b-instruct', 'Qwen2.5', 'Qwen/Qwen2.5-32B-Instruct', '32B', 131072);

-- Add quantization
INSERT INTO quantization_configs (model_id, quantization, format, file_path, vram_required_gb)
VALUES (
    (SELECT id FROM model_configs WHERE name = 'qwen2.5-32b-instruct'),
    'awq',
    'awq',
    'Qwen/Qwen2.5-32B-Instruct-AWQ',
    20
);

-- Add launch config
INSERT INTO launch_configs (quant_id, runtime, gpu_count, context_length, is_default)
VALUES (
    (SELECT id FROM quantization_configs WHERE model_id =
        (SELECT id FROM model_configs WHERE name = 'qwen2.5-32b-instruct')
        AND quantization = 'awq'),
    'vllm',
    1,
    32768,
    TRUE
);
```

### Phase 2: HuggingFace Integration

In Phase 2, models can be discovered and downloaded from HuggingFace:

1. User searches for model in Dashboard UI
2. Dashboard queries HuggingFace API for model info
3. User selects quantization/format to download
4. Dashboard triggers download via `huggingface-cli`
5. On completion, Dashboard auto-registers model with estimated VRAM
6. User can adjust launch config (context length, parallelism)

---

## Runtime-Specific Configuration

### vLLM Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--model` | Model path | Required |
| `--max-model-len` | Max context length | 8192 |
| `--tensor-parallel-size` | TP degree | 1 |
| `--pipeline-parallel-size` | PP degree | 1 |
| `--max-num-seqs` | Max concurrent requests | 256 |
| `--gpu-memory-utilization` | VRAM fraction to use | 0.9 |
| `--quantization` | Quantization method | auto |
| `--dtype` | Data type | auto |
| `--trust-remote-code` | Allow custom model code | false |
| `--enable-prefix-caching` | Enable prefix caching | false |

### SGLang Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--model-path` | Model path | Required |
| `--context-length` | Max context length | 8192 |
| `--tp` | Tensor parallelism degree | 1 |
| `--max-running-requests` | Max concurrent requests | 256 |
| `--mem-fraction-static` | Static memory fraction | 0.9 |
| `--quantization` | Quantization method | None |
| `--trust-remote-code` | Allow custom model code | false |

### llama.cpp Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `-m` | Model file path | Required |
| `-c` | Context size | 512 |
| `-ngl` | Layers to offload to GPU | 0 |
| `-np` | Number of parallel sequences | 1 |
| `-b` | Batch size | 512 |
| `--host` | Listen host | 127.0.0.1 |
| `--port` | Listen port | 8080 |

---

## Troubleshooting Guide

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| OOM during load | Insufficient VRAM | Reduce context length or use smaller quant |
| Slow token generation | GPU memory thrashing | Increase `--gpu-memory-utilization` |
| Container won't start | Missing CUDA libraries | Verify nvidia-container-toolkit installed |
| Model not found | Wrong path | Check HuggingFace directory structure |
| NCCL errors | Multi-GPU communication | Check `NCCL_DEBUG=INFO` logs |
| Ray connection failed | Network issues | Verify machines can reach each other |

### Health Check Debugging

```bash
# Check if container is running
podman ps -a --filter label=llm-serve=true

# View container logs
podman logs llm-qwen2.5-32b-instruct-awq-a1b2c3d4

# Test health endpoint directly
curl http://localhost:8001/health

# Test inference
curl http://localhost:8001/v1/models
```

---

## Best Practices

### Memory Management

1. **Leave headroom**: Set `--gpu-memory-utilization 0.95` max to avoid OOM
2. **Size context appropriately**: Larger context = more VRAM, only use what you need
3. **Quantize large models**: 70B+ models benefit significantly from AWQ/GPTQ

### Performance Tuning

1. **Tensor parallelism**: Use TP for latency-sensitive workloads (same-machine)
2. **Pipeline parallelism**: Use PP when mixing VRAM sizes or crossing machines
3. **Batch size**: Increase `--max-num-seqs` for throughput, decrease for latency
4. **Prefix caching**: Enable for repetitive prompts (e.g., system prompts)

### Reliability

1. **Health checks**: Always wait for `/health` before routing traffic
2. **Graceful shutdown**: Allow 30s for container cleanup
3. **Resource isolation**: Use dedicated GPUs per model, don't share

---

## Related Documents

- [Architecture Overview](./architecture-overview.md)
- [Dashboard Architecture](./architecture-dashboard.md)
- [Daemon Architecture](./architecture-daemon.md)
- [Product Requirements](./llms-prd.md)
