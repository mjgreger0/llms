# Container Library Seed Data

This directory contains SQL scripts to populate the database with initial vLLM configurations for common open-source language models.

## Contents

The seed data includes:

- **7 popular models** across 3 model families:
  - Qwen 2.5: 72B, 32B, 14B, 7B (Instruct variants)
  - Llama 3.1: 70B, 8B (Instruct variants)
  - Mistral: 7B v0.3 (Instruct)

- **Multiple quantization options** per model:
  - Large models (70B+): AWQ (4-bit), FP16 (multi-GPU)
  - Medium models (14B-32B): AWQ, FP16, Q4_K_M
  - Small models (7B-8B): AWQ, FP16, Q4_K_M, Q8_0

- **Production-ready container configurations** for vLLM runtime with:
  - Optimized context lengths (32K for most, 128K for Llama 3.1)
  - Tensor parallelism for multi-GPU setups
  - Default parallel request settings

## How to Run

### Method 1: Using psql (Recommended)

```bash
# From the project root
cd dashboard/backend/db/seed_data

# Run the seed script
psql -U postgres -d llm_dashboard -f container_library.sql
```

### Method 2: Using Docker/Podman with PostgreSQL container

```bash
# Copy file to container
docker cp container_library.sql postgres-container:/tmp/

# Execute inside container
docker exec -it postgres-container psql -U postgres -d llm_dashboard -f /tmp/container_library.sql
```

### Method 3: From Python (using SQLAlchemy)

```python
from dashboard.backend.db.session import engine

with open('dashboard/backend/db/seed_data/container_library.sql', 'r') as f:
    sql = f.read()

with engine.connect() as conn:
    conn.execute(sql)
    conn.commit()
```

## VRAM Calculation Formula

VRAM requirements are calculated using the formula:

```
VRAM (GB) = (Parameters × Bits_per_param / 8) × 1.2
```

Where:
- **Parameters**: Number of model parameters in billions (e.g., 72B)
- **Bits_per_param**: Quantization level
  - FP16: 16 bits
  - AWQ: 4 bits (approximate)
  - Q8_0: 8 bits
  - Q4_K_M: 4 bits (approximate)
- **1.2 multiplier**: 20% overhead for:
  - KV cache
  - Activation memory
  - Intermediate tensors
  - Runtime overhead

### Examples

**Qwen 2.5 72B AWQ (4-bit)**:
```
72B × 4 / 8 × 1.2 = 43.2 GB
Split across 2 GPUs → ~21.6 GB per GPU
Rounded to 36 GB for safety margin
```

**Llama 3.1 8B FP16**:
```
8B × 16 / 8 × 1.2 = 19.2 GB
Rounded to 16 GB for safety margin
```

**Mistral 7B Q4_K_M**:
```
7B × 4 / 8 × 1.2 = 4.2 GB
Rounded to 3.5 GB for safety margin
```

## Multi-GPU Configurations

Models requiring more than 48GB VRAM use tensor parallelism:

| Model | Quantization | Total VRAM | GPU Count | Strategy |
|-------|-------------|-----------|-----------|----------|
| Qwen 2.5 72B | FP16 | 144 GB | 4 | Tensor parallel (TP=4) |
| Qwen 2.5 72B | AWQ | 36 GB | 2 | Tensor parallel (TP=2) |
| Llama 3.1 70B | FP16 | 140 GB | 4 | Tensor parallel (TP=4) |
| Llama 3.1 70B | AWQ | 35 GB | 2 | Tensor parallel (TP=2) |
| Qwen 2.5 32B | FP16 | 64 GB | 2 | Tensor parallel (TP=2) |

All other configurations use single GPU (TP=1).

## Adding New Models

To add a new model to the seed data:

### 1. Add the base model

```sql
INSERT INTO models (name, provider, huggingface_id, base_parameters) VALUES
  ('model-name', 'Provider', 'org/model-id', 'XXB')
ON CONFLICT (name) DO NOTHING;
```

### 2. Add quantization variants

```sql
INSERT INTO model_quantizations (model_id, quantization, file_path, file_size_gb, vram_required_gb, gpu_count) VALUES
  ((SELECT id FROM models WHERE name = 'model-name'),
   'awq', 'org/model-awq', <file_size>, <vram_required>, <gpu_count>)
ON CONFLICT (model_id, quantization) DO NOTHING;
```

Calculate VRAM using the formula above.

### 3. Add container configuration

```sql
INSERT INTO container_configs (model_quant_id, runtime, context_length, max_parallel, tensor_parallel, pipeline_parallel, extra_args)
SELECT id, 'vllm', <context_length>, 4, <tensor_parallel>, 1, NULL
FROM model_quantizations
WHERE model_id = (SELECT id FROM models WHERE name = 'model-name')
  AND quantization = '<quantization>'
ON CONFLICT DO NOTHING;
```

Set `tensor_parallel` equal to `gpu_count` from step 2.

### 4. Guidelines for new models

- **Context length**: Use model's maximum context (check HuggingFace model card)
- **Max parallel**: Default to 4 (concurrent requests)
- **Tensor parallel**: Match GPU count (1 for single GPU, 2/4/8 for multi-GPU)
- **Pipeline parallel**: Keep at 1 (not commonly used)
- **Extra args**: Set to NULL initially, customize per deployment

## Quantization Types

| Type | Bits | Quality | Speed | Use Case |
|------|------|---------|-------|----------|
| **FP16** | 16 | Highest | Slower | Production, benchmarks |
| **AWQ** | ~4 | High | Fast | Production, resource-constrained |
| **Q8_0** | 8 | Very High | Medium | Balanced quality/performance |
| **Q4_K_M** | ~4 | Good | Fast | Development, testing |

## HuggingFace Paths

The `file_path` in model_quantizations points to HuggingFace repositories:

- **Official models**: Use official org names (e.g., `Qwen/`, `meta-llama/`, `mistralai/`)
- **Quantized models**: Often from community members (e.g., `casperhansen/`, `TheBloke/`, `bartowski/`)
- **GGUF models**: Typically have `-GGUF` suffix in repo name

When deploying, vLLM or llama.cpp will download these models on first use.

## Verification Queries

After loading seed data, verify with these queries:

### List all models and quantizations

```sql
SELECT
  m.name,
  m.provider,
  m.base_parameters,
  mq.quantization,
  mq.vram_required_gb,
  mq.gpu_count
FROM models m
JOIN model_quantizations mq ON m.id = mq.model_id
ORDER BY m.name, mq.quantization;
```

### Show container configurations

```sql
SELECT
  m.name,
  mq.quantization,
  cc.runtime,
  cc.context_length,
  cc.tensor_parallel,
  mq.vram_required_gb || ' GB VRAM' as memory
FROM container_configs cc
JOIN model_quantizations mq ON cc.model_quant_id = mq.id
JOIN models m ON mq.model_id = m.id
ORDER BY m.name, mq.quantization;
```

### Count by model size

```sql
SELECT
  m.base_parameters,
  COUNT(DISTINCT m.id) as model_count,
  COUNT(mq.id) as quantization_count
FROM models m
LEFT JOIN model_quantizations mq ON m.id = mq.model_id
GROUP BY m.base_parameters
ORDER BY m.base_parameters;
```

## Idempotency

All INSERT statements use `ON CONFLICT DO NOTHING` to make the script safe to run multiple times. Running the script again will:

- Skip models that already exist (by name)
- Skip quantizations that already exist (by model_id + quantization)
- Skip container configs if they already exist

This allows you to:
- Safely re-run after errors
- Add new models without affecting existing ones
- Update the script and re-run with new additions

## Notes

- **Transaction safety**: All operations are wrapped in a transaction (BEGIN/COMMIT)
- **Foreign keys**: Cascade deletes ensure cleanup when models are removed
- **Defaults**: Container configs use sensible defaults from schema (can be customized per deployment)
- **Extra args**: Set to NULL; customize later via API for specific deployments (e.g., `--max-model-len`, `--gpu-memory-utilization`)

## Future Enhancements

Potential additions to seed data:

1. **More model families**:
   - DeepSeek Coder
   - CodeLlama
   - Phi-3
   - Gemma 2

2. **Additional quantizations**:
   - GPTQ variants
   - BF16 for specific hardware

3. **Specialized configs**:
   - Long context variants (>128K)
   - Speculative decoding setups
   - LoRA adapter configurations

4. **Performance profiles**:
   - Token throughput estimates
   - Latency benchmarks
   - Recommended batch sizes
