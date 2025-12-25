-- ============================================================================
-- Container Library Seed Data
-- ============================================================================
-- This script populates the database with initial vLLM configurations for
-- common open-source LLMs, including multiple quantization options and
-- optimized container configurations.
--
-- VRAM estimates use formula: params_B * bits / 8 * 1.2
-- (20% overhead for KV cache, activations, etc.)
--
-- Usage: psql -U postgres -d llm_dashboard -f container_library.sql
-- ============================================================================

BEGIN;

-- ============================================================================
-- MODELS: Base model definitions
-- ============================================================================
-- Define the core models without quantization details

INSERT INTO models (name, provider, huggingface_id, base_parameters) VALUES
  -- Qwen 2.5 family (Alibaba Cloud)
  ('qwen2.5-72b-instruct', 'Qwen', 'Qwen/Qwen2.5-72B-Instruct', '72B'),
  ('qwen2.5-32b-instruct', 'Qwen', 'Qwen/Qwen2.5-32B-Instruct', '32B'),
  ('qwen2.5-14b-instruct', 'Qwen', 'Qwen/Qwen2.5-14B-Instruct', '14B'),
  ('qwen2.5-7b-instruct', 'Qwen', 'Qwen/Qwen2.5-7B-Instruct', '7B'),

  -- Llama 3.1 family (Meta)
  ('llama-3.1-70b-instruct', 'Meta', 'meta-llama/Meta-Llama-3.1-70B-Instruct', '70B'),
  ('llama-3.1-8b-instruct', 'Meta', 'meta-llama/Meta-Llama-3.1-8B-Instruct', '8B'),

  -- Mistral family
  ('mistral-7b-v0.3', 'Mistral AI', 'mistralai/Mistral-7B-Instruct-v0.3', '7B')
ON CONFLICT (name) DO NOTHING;


-- ============================================================================
-- MODEL QUANTIZATIONS: Quantized versions with VRAM requirements
-- ============================================================================
-- Each model can have multiple quantization options with different memory/quality tradeoffs

-- Qwen 2.5 72B Instruct
-- Large model: AWQ and FP16 options
INSERT INTO model_quantizations (model_id, quantization, file_path, file_size_gb, vram_required_gb, gpu_count) VALUES
  ((SELECT id FROM models WHERE name = 'qwen2.5-72b-instruct'),
   'awq', 'Qwen/Qwen2.5-72B-Instruct-AWQ', 40.0, 36.0, 2),  -- 72B * 4 / 8 * 1.2 = 43.2, using 2 GPUs

  ((SELECT id FROM models WHERE name = 'qwen2.5-72b-instruct'),
   'fp16', 'Qwen/Qwen2.5-72B-Instruct', 144.0, 144.0, 4)  -- 72B * 16 / 8 * 1.2 = 172.8, using 4 GPUs
ON CONFLICT (model_id, quantization) DO NOTHING;

-- Qwen 2.5 32B Instruct
-- Medium model: AWQ, FP16, and Q4_K_M options
INSERT INTO model_quantizations (model_id, quantization, file_path, file_size_gb, vram_required_gb, gpu_count) VALUES
  ((SELECT id FROM models WHERE name = 'qwen2.5-32b-instruct'),
   'awq', 'Qwen/Qwen2.5-32B-Instruct-AWQ', 18.0, 16.0, 1),  -- 32B * 4 / 8 * 1.2 = 19.2

  ((SELECT id FROM models WHERE name = 'qwen2.5-32b-instruct'),
   'fp16', 'Qwen/Qwen2.5-32B-Instruct', 64.0, 64.0, 2),  -- 32B * 16 / 8 * 1.2 = 76.8, using 2 GPUs

  ((SELECT id FROM models WHERE name = 'qwen2.5-32b-instruct'),
   'q4_k_m', 'Qwen/Qwen2.5-32B-Instruct-GGUF', 18.0, 16.0, 1)  -- Similar to AWQ
ON CONFLICT (model_id, quantization) DO NOTHING;

-- Qwen 2.5 14B Instruct
-- Medium model: AWQ, FP16, and Q4_K_M options
INSERT INTO model_quantizations (model_id, quantization, file_path, file_size_gb, vram_required_gb, gpu_count) VALUES
  ((SELECT id FROM models WHERE name = 'qwen2.5-14b-instruct'),
   'awq', 'Qwen/Qwen2.5-14B-Instruct-AWQ', 8.0, 7.0, 1),  -- 14B * 4 / 8 * 1.2 = 8.4

  ((SELECT id FROM models WHERE name = 'qwen2.5-14b-instruct'),
   'fp16', 'Qwen/Qwen2.5-14B-Instruct', 28.0, 28.0, 1),  -- 14B * 16 / 8 * 1.2 = 33.6

  ((SELECT id FROM models WHERE name = 'qwen2.5-14b-instruct'),
   'q4_k_m', 'Qwen/Qwen2.5-14B-Instruct-GGUF', 8.0, 7.0, 1)
ON CONFLICT (model_id, quantization) DO NOTHING;

-- Qwen 2.5 7B Instruct
-- Small model: AWQ, FP16, Q4_K_M, and Q8_0 options
INSERT INTO model_quantizations (model_id, quantization, file_path, file_size_gb, vram_required_gb, gpu_count) VALUES
  ((SELECT id FROM models WHERE name = 'qwen2.5-7b-instruct'),
   'awq', 'Qwen/Qwen2.5-7B-Instruct-AWQ', 4.0, 3.5, 1),  -- 7B * 4 / 8 * 1.2 = 4.2

  ((SELECT id FROM models WHERE name = 'qwen2.5-7b-instruct'),
   'fp16', 'Qwen/Qwen2.5-7B-Instruct', 14.0, 14.0, 1),  -- 7B * 16 / 8 * 1.2 = 16.8

  ((SELECT id FROM models WHERE name = 'qwen2.5-7b-instruct'),
   'q4_k_m', 'Qwen/Qwen2.5-7B-Instruct-GGUF', 4.0, 3.5, 1),

  ((SELECT id FROM models WHERE name = 'qwen2.5-7b-instruct'),
   'q8_0', 'Qwen/Qwen2.5-7B-Instruct-GGUF', 7.5, 7.0, 1)  -- 7B * 8 / 8 * 1.2 = 8.4
ON CONFLICT (model_id, quantization) DO NOTHING;

-- Llama 3.1 70B Instruct
-- Large model: AWQ and FP16 options
INSERT INTO model_quantizations (model_id, quantization, file_path, file_size_gb, vram_required_gb, gpu_count) VALUES
  ((SELECT id FROM models WHERE name = 'llama-3.1-70b-instruct'),
   'awq', 'casperhansen/llama-3.1-70b-instruct-awq', 38.0, 35.0, 2),  -- 70B * 4 / 8 * 1.2 = 42

  ((SELECT id FROM models WHERE name = 'llama-3.1-70b-instruct'),
   'fp16', 'meta-llama/Meta-Llama-3.1-70B-Instruct', 140.0, 140.0, 4)  -- 70B * 16 / 8 * 1.2 = 168, using 4 GPUs
ON CONFLICT (model_id, quantization) DO NOTHING;

-- Llama 3.1 8B Instruct
-- Small model: AWQ, FP16, Q4_K_M, and Q8_0 options
INSERT INTO model_quantizations (model_id, quantization, file_path, file_size_gb, vram_required_gb, gpu_count) VALUES
  ((SELECT id FROM models WHERE name = 'llama-3.1-8b-instruct'),
   'awq', 'casperhansen/llama-3.1-8b-instruct-awq', 5.0, 4.0, 1),  -- 8B * 4 / 8 * 1.2 = 4.8

  ((SELECT id FROM models WHERE name = 'llama-3.1-8b-instruct'),
   'fp16', 'meta-llama/Meta-Llama-3.1-8B-Instruct', 16.0, 16.0, 1),  -- 8B * 16 / 8 * 1.2 = 19.2

  ((SELECT id FROM models WHERE name = 'llama-3.1-8b-instruct'),
   'q4_k_m', 'bartowski/Meta-Llama-3.1-8B-Instruct-GGUF', 5.0, 4.5, 1),

  ((SELECT id FROM models WHERE name = 'llama-3.1-8b-instruct'),
   'q8_0', 'bartowski/Meta-Llama-3.1-8B-Instruct-GGUF', 8.5, 8.0, 1)  -- 8B * 8 / 8 * 1.2 = 9.6
ON CONFLICT (model_id, quantization) DO NOTHING;

-- Mistral 7B v0.3 Instruct
-- Small model: AWQ, FP16, Q4_K_M, and Q8_0 options
INSERT INTO model_quantizations (model_id, quantization, file_path, file_size_gb, vram_required_gb, gpu_count) VALUES
  ((SELECT id FROM models WHERE name = 'mistral-7b-v0.3'),
   'awq', 'TheBloke/Mistral-7B-Instruct-v0.3-AWQ', 4.0, 3.5, 1),  -- 7B * 4 / 8 * 1.2 = 4.2

  ((SELECT id FROM models WHERE name = 'mistral-7b-v0.3'),
   'fp16', 'mistralai/Mistral-7B-Instruct-v0.3', 14.0, 14.0, 1),  -- 7B * 16 / 8 * 1.2 = 16.8

  ((SELECT id FROM models WHERE name = 'mistral-7b-v0.3'),
   'q4_k_m', 'TheBloke/Mistral-7B-Instruct-v0.3-GGUF', 4.0, 3.5, 1),

  ((SELECT id FROM models WHERE name = 'mistral-7b-v0.3'),
   'q8_0', 'TheBloke/Mistral-7B-Instruct-v0.3-GGUF', 7.5, 7.0, 1)  -- 7B * 8 / 8 * 1.2 = 8.4
ON CONFLICT (model_id, quantization) DO NOTHING;


-- ============================================================================
-- CONTAINER CONFIGS: vLLM runtime configurations
-- ============================================================================
-- Production-ready configurations for each model quantization
-- These settings are optimized for inference performance and can be customized

-- Qwen 2.5 72B AWQ (2 GPUs, tensor parallel)
INSERT INTO container_configs (model_quant_id, runtime, context_length, max_parallel, tensor_parallel, pipeline_parallel, extra_args)
SELECT id, 'vllm', 32768, 4, 2, 1, NULL
FROM model_quantizations
WHERE model_id = (SELECT id FROM models WHERE name = 'qwen2.5-72b-instruct')
  AND quantization = 'awq'
ON CONFLICT DO NOTHING;

-- Qwen 2.5 72B FP16 (4 GPUs, tensor parallel)
INSERT INTO container_configs (model_quant_id, runtime, context_length, max_parallel, tensor_parallel, pipeline_parallel, extra_args)
SELECT id, 'vllm', 32768, 4, 4, 1, NULL
FROM model_quantizations
WHERE model_id = (SELECT id FROM models WHERE name = 'qwen2.5-72b-instruct')
  AND quantization = 'fp16'
ON CONFLICT DO NOTHING;

-- Qwen 2.5 32B AWQ (1 GPU)
INSERT INTO container_configs (model_quant_id, runtime, context_length, max_parallel, tensor_parallel, pipeline_parallel, extra_args)
SELECT id, 'vllm', 32768, 4, 1, 1, NULL
FROM model_quantizations
WHERE model_id = (SELECT id FROM models WHERE name = 'qwen2.5-32b-instruct')
  AND quantization = 'awq'
ON CONFLICT DO NOTHING;

-- Qwen 2.5 32B FP16 (2 GPUs, tensor parallel)
INSERT INTO container_configs (model_quant_id, runtime, context_length, max_parallel, tensor_parallel, pipeline_parallel, extra_args)
SELECT id, 'vllm', 32768, 4, 2, 1, NULL
FROM model_quantizations
WHERE model_id = (SELECT id FROM models WHERE name = 'qwen2.5-32b-instruct')
  AND quantization = 'fp16'
ON CONFLICT DO NOTHING;

-- Qwen 2.5 32B Q4_K_M (1 GPU)
INSERT INTO container_configs (model_quant_id, runtime, context_length, max_parallel, tensor_parallel, pipeline_parallel, extra_args)
SELECT id, 'vllm', 32768, 4, 1, 1, NULL
FROM model_quantizations
WHERE model_id = (SELECT id FROM models WHERE name = 'qwen2.5-32b-instruct')
  AND quantization = 'q4_k_m'
ON CONFLICT DO NOTHING;

-- Qwen 2.5 14B AWQ (1 GPU)
INSERT INTO container_configs (model_quant_id, runtime, context_length, max_parallel, tensor_parallel, pipeline_parallel, extra_args)
SELECT id, 'vllm', 32768, 4, 1, 1, NULL
FROM model_quantizations
WHERE model_id = (SELECT id FROM models WHERE name = 'qwen2.5-14b-instruct')
  AND quantization = 'awq'
ON CONFLICT DO NOTHING;

-- Qwen 2.5 14B FP16 (1 GPU)
INSERT INTO container_configs (model_quant_id, runtime, context_length, max_parallel, tensor_parallel, pipeline_parallel, extra_args)
SELECT id, 'vllm', 32768, 4, 1, 1, NULL
FROM model_quantizations
WHERE model_id = (SELECT id FROM models WHERE name = 'qwen2.5-14b-instruct')
  AND quantization = 'fp16'
ON CONFLICT DO NOTHING;

-- Qwen 2.5 14B Q4_K_M (1 GPU)
INSERT INTO container_configs (model_quant_id, runtime, context_length, max_parallel, tensor_parallel, pipeline_parallel, extra_args)
SELECT id, 'vllm', 32768, 4, 1, 1, NULL
FROM model_quantizations
WHERE model_id = (SELECT id FROM models WHERE name = 'qwen2.5-14b-instruct')
  AND quantization = 'q4_k_m'
ON CONFLICT DO NOTHING;

-- Qwen 2.5 7B - All quantizations (1 GPU each)
INSERT INTO container_configs (model_quant_id, runtime, context_length, max_parallel, tensor_parallel, pipeline_parallel, extra_args)
SELECT id, 'vllm', 32768, 4, 1, 1, NULL
FROM model_quantizations
WHERE model_id = (SELECT id FROM models WHERE name = 'qwen2.5-7b-instruct')
ON CONFLICT DO NOTHING;

-- Llama 3.1 70B AWQ (2 GPUs, tensor parallel)
INSERT INTO container_configs (model_quant_id, runtime, context_length, max_parallel, tensor_parallel, pipeline_parallel, extra_args)
SELECT id, 'vllm', 131072, 4, 2, 1, NULL  -- Llama 3.1 supports 128K context
FROM model_quantizations
WHERE model_id = (SELECT id FROM models WHERE name = 'llama-3.1-70b-instruct')
  AND quantization = 'awq'
ON CONFLICT DO NOTHING;

-- Llama 3.1 70B FP16 (4 GPUs, tensor parallel)
INSERT INTO container_configs (model_quant_id, runtime, context_length, max_parallel, tensor_parallel, pipeline_parallel, extra_args)
SELECT id, 'vllm', 131072, 4, 4, 1, NULL  -- Llama 3.1 supports 128K context
FROM model_quantizations
WHERE model_id = (SELECT id FROM models WHERE name = 'llama-3.1-70b-instruct')
  AND quantization = 'fp16'
ON CONFLICT DO NOTHING;

-- Llama 3.1 8B - All quantizations (1 GPU each)
INSERT INTO container_configs (model_quant_id, runtime, context_length, max_parallel, tensor_parallel, pipeline_parallel, extra_args)
SELECT id, 'vllm', 131072, 4, 1, 1, NULL  -- Llama 3.1 supports 128K context
FROM model_quantizations
WHERE model_id = (SELECT id FROM models WHERE name = 'llama-3.1-8b-instruct')
ON CONFLICT DO NOTHING;

-- Mistral 7B v0.3 - All quantizations (1 GPU each)
INSERT INTO container_configs (model_quant_id, runtime, context_length, max_parallel, tensor_parallel, pipeline_parallel, extra_args)
SELECT id, 'vllm', 32768, 4, 1, 1, NULL
FROM model_quantizations
WHERE model_id = (SELECT id FROM models WHERE name = 'mistral-7b-v0.3')
ON CONFLICT DO NOTHING;

COMMIT;

-- ============================================================================
-- Verification queries (uncomment to run)
-- ============================================================================

-- Show all models with their quantizations
-- SELECT
--   m.name,
--   m.provider,
--   m.base_parameters,
--   mq.quantization,
--   mq.vram_required_gb,
--   mq.gpu_count
-- FROM models m
-- JOIN model_quantizations mq ON m.id = mq.model_id
-- ORDER BY m.name, mq.quantization;

-- Show all container configs
-- SELECT
--   m.name,
--   mq.quantization,
--   cc.runtime,
--   cc.context_length,
--   cc.tensor_parallel,
--   mq.vram_required_gb || ' GB VRAM' as memory
-- FROM container_configs cc
-- JOIN model_quantizations mq ON cc.model_quant_id = mq.id
-- JOIN models m ON mq.model_id = m.id
-- ORDER BY m.name, mq.quantization;

-- Count by model size
-- SELECT
--   m.base_parameters,
--   COUNT(DISTINCT m.id) as model_count,
--   COUNT(mq.id) as quantization_count
-- FROM models m
-- LEFT JOIN model_quantizations mq ON m.id = mq.model_id
-- GROUP BY m.base_parameters
-- ORDER BY m.base_parameters;
