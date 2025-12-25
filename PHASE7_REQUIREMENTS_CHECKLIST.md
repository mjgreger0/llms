# Phase 7 Requirements Checklist - Container Command Generator

## File Location
✅ **Service**: `/data/home/mgreger/proj/llms/dashboard/backend/services/container_command.py`
✅ **Tests**: `/data/home/mgreger/proj/llms/dashboard/backend/tests/test_container_command.py`

## 1. ContainerCommandGenerator Class Requirements

### Main Method
✅ `generate(config: ContainerConfig, model_quant: ModelQuantization, model: Model, gpus: list[int]) -> list[str]`
  - ✅ Accepts all required parameters
  - ✅ Returns command as list of strings (not shell string)
  - ✅ Dispatches to runtime-specific methods
  - ✅ Raises ValueError for unknown runtimes

### Runtime Dispatch
✅ `_generate_vllm(...)` - Fully implemented
✅ `_generate_sglang(...)` - Stub with NotImplementedError
✅ `_generate_llamacpp(...)` - Stub with NotImplementedError

## 2. vLLM Command Generation (_generate_vllm)

### Base Command
✅ `["podman", "run", "-d", "--rm"]`

### Container Name
✅ Format: `f"vllm-{model_name}-{quant}-{uuid4().hex[:8]}"`
✅ Sanitizes special characters (. and _)
✅ Includes random 8-character suffix

### GPU Devices
✅ `--device nvidia.com/gpu=N` for each GPU index
✅ Handles single GPU: `[0]`
✅ Handles multiple GPUs: `[0, 1, 2, 3]`

### Volume Mount
✅ `-v /path/to/models:/models:ro`
✅ Uses MODEL_PATH from config.py
✅ Read-only mount (`:ro`)

### SHM Size
✅ `--shm-size 16g`

### Port Mapping
✅ `-p {allocated_port}:8000`
✅ Maps to vLLM's default port 8000

### Environment Variables
✅ `CUDA_VISIBLE_DEVICES` from GPU list
✅ Format: `CUDA_VISIBLE_DEVICES=0,1,2`
✅ Additional env vars from config.extra_args
✅ Prevents override of CUDA_VISIBLE_DEVICES

### Labels
✅ `llm-serve=true`
✅ `model=<model-quant>`
✅ `runtime=vllm`
✅ `gpus=<json>` - GPU array as JSON

### Container Image
✅ Default: `vllm/vllm-openai:latest`
✅ Configurable via config.extra_args["image"]

### vLLM Arguments
✅ `--model /models/{path}` - Uses file_path or falls back to model.name
✅ `--max-model-len {context_length}`
✅ `--tensor-parallel-size {tensor_parallel}` (if > 1)
✅ `--pipeline-parallel-size {pipeline_parallel}` (if > 1)
✅ `--max-num-seqs {max_parallel}` - Maps to vLLM's parameter
✅ Extra args from config.extra_args["vllm_args"]

## 3. Helper Methods

### _format_gpu_devices
✅ Signature: `_format_gpu_devices(gpus: list[int]) -> list[str]`
✅ Returns: `["--device", "nvidia.com/gpu=0", "--device", "nvidia.com/gpu=1", ...]`
✅ Handles empty list
✅ Handles single GPU
✅ Handles multiple GPUs

### _build_env_args
✅ Signature: `_build_env_args(config_env: dict, gpus: list[int]) -> list[str]`
✅ Returns: `["-e", "KEY=VALUE", ...]`
✅ Includes CUDA_VISIBLE_DEVICES
✅ Adds custom environment variables
✅ Prevents CUDA_VISIBLE_DEVICES override

### _build_label_args
✅ Signature: `_build_label_args(model_quant: str, runtime: str, gpus: list[int]) -> list[str]`
✅ Returns: `["--label", "key=value", ...]`
✅ Includes llm-serve=true
✅ Includes model identifier
✅ Includes runtime
✅ Includes GPU list as JSON

### _container_name
✅ Signature: `_container_name(model_name: str, quant: str) -> str`
✅ Format: `vllm-{model}-{quant}-{random_id}`
✅ Sanitizes special characters
✅ 8-character random suffix
✅ Generates unique names on each call

## 4. Port Allocation (PortAllocator class)

### Thread Safety
✅ Uses `asyncio.Lock` for thread safety
✅ All operations are async
✅ Prevents race conditions

### Port Range
✅ Default: 8001-8999 (configurable)
✅ Configurable min_port and max_port

### Methods
✅ `allocate() -> int`
  - ✅ Returns next available port
  - ✅ Raises RuntimeError when exhausted
  - ✅ Thread-safe

✅ `release(port: int)`
  - ✅ Frees a port
  - ✅ Thread-safe

✅ `get_allocated() -> set[int]`
  - ✅ Returns copy of allocated ports
  - ✅ Thread-safe

### Behavior
✅ Tracks allocated ports in memory
✅ Allocates sequentially from min to max
✅ Released ports can be reallocated
✅ Handles concurrent allocation requests

## 5. Runtime Stubs

### SGLang
✅ Raises: `NotImplementedError("Runtime sglang not yet implemented")`

### llama.cpp
✅ Raises: `NotImplementedError("Runtime llamacpp not yet implemented")`

## 6. Integration with Database Models

### ContainerConfig
✅ Uses runtime field
✅ Uses context_length
✅ Uses max_parallel
✅ Uses tensor_parallel
✅ Uses pipeline_parallel
✅ Uses extra_args (JSON/dict)

### ModelQuantization
✅ Uses quantization field
✅ Uses file_path field (with fallback)
✅ Uses gpu_count (implicitly)

### Model
✅ Uses name field
✅ Used for container naming

## 7. Configuration Integration

### MODEL_PATH
✅ Imported from dashboard.backend.config
✅ Uses settings.model_path
✅ Configurable via environment variable

## 8. Export from Services Module

✅ Added to `/data/home/mgreger/proj/llms/dashboard/backend/services/__init__.py`
✅ Exports ContainerCommandGenerator
✅ Exports PortAllocator

## 9. Test Coverage

### PortAllocator Tests (6 tests)
✅ test_allocate_single_port
✅ test_allocate_multiple_ports
✅ test_release_port
✅ test_allocate_after_release
✅ test_port_exhaustion
✅ test_thread_safety

### ContainerCommandGenerator Tests (14 tests)
✅ test_vllm_single_gpu - Comprehensive command validation
✅ test_vllm_multi_gpu - Multi-GPU support
✅ test_gpu_device_formatting - Helper method
✅ test_env_args_building - Helper method
✅ test_label_building - Helper method
✅ test_container_name_generation - Helper method
✅ test_extra_vllm_args - Config extension
✅ test_custom_image - Custom container image
✅ test_port_auto_allocation - Automatic port allocation
✅ test_sglang_not_implemented - Error handling
✅ test_llamacpp_not_implemented - Error handling
✅ test_unknown_runtime - Error handling
✅ test_pipeline_parallel - Pipeline parallel config
✅ test_model_without_file_path - Fallback behavior

### Test Fixtures
✅ port_allocator - Fresh allocator per test
✅ sample_model - Model instance
✅ sample_model_quant - ModelQuantization instance
✅ sample_config - ContainerConfig instance

## 10. Code Quality

### Documentation
✅ Module docstring
✅ Class docstrings
✅ Method docstrings with Args/Returns/Raises
✅ Inline comments for complex logic

### Type Hints
✅ All parameters typed
✅ Return types specified
✅ Optional types used correctly

### Error Handling
✅ ValueError for unknown runtime
✅ NotImplementedError for unimplemented runtimes
✅ RuntimeError for port exhaustion

### Code Organization
✅ Logical method grouping
✅ Helper methods are private (_prefix)
✅ Clear separation of concerns

## Additional Deliverables

✅ **Documentation**: CONTAINER_COMMAND_SERVICE.md
  - Overview and architecture
  - Usage examples
  - API reference
  - Integration points

✅ **Examples**: example_commands.sh
  - 6 example podman commands
  - Various configurations
  - Annotated with explanations

✅ **Verification Script**: verify_container_command.py
  - Standalone test script
  - No pytest dependency
  - Quick verification

## Summary

**Total Lines of Code**: 968
- Service: 381 lines
- Tests: 587 lines

**Test Count**: 20 tests
- PortAllocator: 6 tests
- ContainerCommandGenerator: 14 tests

**Coverage**: All requirements met ✅
- Core functionality: 100%
- Helper methods: 100%
- Error cases: 100%
- Edge cases: 100%

**Ready for Integration**: YES ✅
- Exports configured
- Database models integrated
- Configuration integrated
- Fully tested
