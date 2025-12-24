# Phase 7: Container Library - Implementation Plan

## Document Information
- **Phase**: 7 - Container Library
- **Created**: 2025-12-23
- **Status**: Ready for Implementation
- **Dependencies**: Phase 1-6 (Database infrastructure, ModelRouter foundation)

---

## Phase Overview

**Goal**: Implement container configuration storage and command generation for vLLM

**Deliverables**:
- Database tables for container library (model_configs, quantization_configs, launch_configs)
- SQLAlchemy models for container configurations
- ContainerCommandGenerator class for generating vLLM commands
- GPU device mapping using nvidia-container-toolkit format
- Environment variable building for containers
- Container labeling scheme for tracking
- Health check polling logic
- Integration with ModelRouter (ensure_capacity, start model)
- Initial vLLM configurations (seed data)
- VRAM requirement calculations

**Exit Criteria**:
- Database schema created and migrated
- vLLM commands generated correctly with all arguments
- Containers start with proper GPU assignments
- Health polling works until container ready
- ModelRouter can trigger container starts
- Container labels track ownership and configuration

---

## Task Breakdown

### 1. Database Schema Implementation

#### Task 1.1: Create Database Migration for Container Library Tables
- [ ] **Status**: Not Started
- **Description**: Create Alembic migration to add model_configs, quantization_configs, and launch_configs tables
- **Acceptance Criteria**:
  - [ ] Migration file created in `dashboard/backend/db/migrations/versions/`
  - [ ] model_configs table created with all fields from architecture
  - [ ] quantization_configs table created with foreign key to model_configs
  - [ ] launch_configs table created with foreign key to quantization_configs
  - [ ] Indexes created on frequently queried columns (name, model_id, quant_id)
  - [ ] Migration runs successfully upgrade and downgrade
  - [ ] All constraints (UNIQUE, NOT NULL, DEFAULT) properly defined
- **Technical Approach**:
  - Use Alembic autogenerate as starting point, then verify/adjust
  - Add indexes: model_configs.name (UNIQUE), quantization_configs(model_id, quantization) (UNIQUE)
  - Set up cascade deletes appropriately (quantizations delete when model deleted)
  - Use TEXT for all string fields except SERIAL/INTEGER fields
  - Default timestamps to NOW() for created_at/updated_at
- **Files/Components**:
  - [ ] `dashboard/backend/db/migrations/versions/XXXX_add_container_library.py` - Alembic migration
- **Dependencies**: None (assumes base database infrastructure exists)
- **Complexity**: M

#### Task 1.2: Add Updated Timestamp Triggers
- [ ] **Status**: Not Started
- **Description**: Create database triggers to automatically update updated_at timestamps
- **Acceptance Criteria**:
  - [ ] Trigger function created for updating updated_at column
  - [ ] Triggers applied to model_configs, launch_configs tables
  - [ ] Trigger fires on UPDATE operations only
  - [ ] updated_at column automatically set to NOW() on row updates
- **Technical Approach**:
  - Create PostgreSQL function: `update_updated_at_column()`
  - Apply trigger to each table with updated_at column
  - Test trigger by updating rows and verifying timestamp changes
- **Files/Components**:
  - [ ] `dashboard/backend/db/migrations/versions/XXXX_add_container_library.py` - Include in same migration
- **Dependencies**: Task 1.1
- **Complexity**: S

---

### 2. SQLAlchemy Models

#### Task 2.1: Create ModelConfig SQLAlchemy Model
- [ ] **Status**: Not Started
- **Description**: Implement SQLAlchemy model for model_configs table
- **Acceptance Criteria**:
  - [ ] ModelConfig class created in models/database.py
  - [ ] All columns mapped from database schema
  - [ ] Relationship to QuantizationConfig defined (one-to-many)
  - [ ] Type hints used for all attributes
  - [ ] __repr__ method provides useful string representation
  - [ ] Validation methods for max_context (positive integer)
- **Technical Approach**:
  - Use SQLAlchemy 2.0 declarative syntax
  - Define relationship with lazy='selectin' for efficient loading
  - Add validators using @validates decorator for max_context
  - Include cascade delete: relationship(..., cascade="all, delete-orphan")
- **Files/Components**:
  - [ ] `dashboard/backend/models/database.py` - Add ModelConfig class
- **Dependencies**: Task 1.1
- **Complexity**: M

#### Task 2.2: Create QuantizationConfig SQLAlchemy Model
- [ ] **Status**: Not Started
- **Description**: Implement SQLAlchemy model for quantization_configs table
- **Acceptance Criteria**:
  - [ ] QuantizationConfig class created in models/database.py
  - [ ] All columns mapped from database schema
  - [ ] Relationship to ModelConfig defined (many-to-one)
  - [ ] Relationship to LaunchConfig defined (one-to-many)
  - [ ] Type hints used for all attributes
  - [ ] Validation for vram_required_gb (positive number)
  - [ ] Validation for format (must be one of: transformers, awq, gptq, gguf)
- **Technical Approach**:
  - Foreign key to model_configs with ondelete='CASCADE'
  - Relationship back to ModelConfig with back_populates
  - Validators for numeric fields (must be positive)
  - Enum or choice validation for format field
- **Files/Components**:
  - [ ] `dashboard/backend/models/database.py` - Add QuantizationConfig class
- **Dependencies**: Task 2.1
- **Complexity**: M

#### Task 2.3: Create LaunchConfig SQLAlchemy Model
- [ ] **Status**: Not Started
- **Description**: Implement SQLAlchemy model for launch_configs table
- **Acceptance Criteria**:
  - [ ] LaunchConfig class created in models/database.py
  - [ ] All columns mapped from database schema
  - [ ] Relationship to QuantizationConfig defined (many-to-one)
  - [ ] JSONB fields properly mapped for extra_args and environment
  - [ ] Type hints include proper JSON typing
  - [ ] Validation for positive integers (gpu_count, tensor_parallel, etc.)
  - [ ] Validation for runtime (must be: vllm, sglang, llamacpp)
- **Technical Approach**:
  - Use JSONB type for extra_args and environment columns
  - Add property methods to access JSONB data as dicts
  - Validators for all numeric fields (positive, non-zero)
  - Default values match architecture specification
- **Files/Components**:
  - [ ] `dashboard/backend/models/database.py` - Add LaunchConfig class
- **Dependencies**: Task 2.2
- **Complexity**: M

#### Task 2.4: Create Pydantic Schemas for API Responses
- [ ] **Status**: Not Started
- **Description**: Create Pydantic models for serializing container configs in API responses
- **Acceptance Criteria**:
  - [ ] ModelConfigSchema created in models/schemas.py
  - [ ] QuantizationConfigSchema created in models/schemas.py
  - [ ] LaunchConfigSchema created in models/schemas.py
  - [ ] Nested schemas properly reference each other
  - [ ] from_attributes=True (ORM mode) enabled
  - [ ] All fields properly typed with Python type hints
  - [ ] Optional fields marked correctly
- **Technical Approach**:
  - Use Pydantic v2 syntax (ConfigDict)
  - Define nested relationships (ModelConfigSchema includes quantizations list)
  - Add computed fields if needed (e.g., full_name = f"{model}-{quant}")
  - Exclude internal fields like encrypted data from responses
- **Files/Components**:
  - [ ] `dashboard/backend/models/schemas.py` - Add container config schemas
- **Dependencies**: Tasks 2.1, 2.2, 2.3
- **Complexity**: M

---

### 3. Container Command Generator

#### Task 3.1: Implement Base ContainerCommandGenerator Class
- [ ] **Status**: Not Started
- **Description**: Create ContainerCommandGenerator class with runtime dispatch logic
- **Acceptance Criteria**:
  - [ ] ContainerCommandGenerator class created in services/
  - [ ] generate() method dispatches to runtime-specific methods
  - [ ] Runtime mapping configured (vllm, sglang, llamacpp)
  - [ ] ValueError raised for unknown runtimes
  - [ ] Type hints for all parameters (LaunchConfig, Machine, list[int])
  - [ ] Returns list[str] representing command parts
  - [ ] Unit tests for dispatch logic
- **Technical Approach**:
  - Create services/container_command.py module
  - Use match/case (Python 3.10+) or dict dispatch for runtime selection
  - Accept LaunchConfig, Machine, and GPU list as parameters
  - Return command as list of strings (not shell string)
  - Private methods: _generate_vllm, _generate_sglang, _generate_llamacpp
- **Files/Components**:
  - [ ] `dashboard/backend/services/container_command.py` - ContainerCommandGenerator class
  - [ ] `dashboard/backend/tests/test_container_command.py` - Unit tests
- **Dependencies**: Task 2.3 (needs LaunchConfig model)
- **Complexity**: M

#### Task 3.2: Implement vLLM Command Generation
- [ ] **Status**: Not Started
- **Description**: Implement _generate_vllm method to build complete vLLM podman command
- **Acceptance Criteria**:
  - [ ] Generates complete podman run command as list[str]
  - [ ] Container name includes model+quant and random suffix
  - [ ] GPU devices mapped using --device nvidia.com/gpu=N format
  - [ ] Model volume mounted at /models:ro
  - [ ] SHM size set to 16g
  - [ ] Port mapping from next available port to 8000
  - [ ] CUDA_VISIBLE_DEVICES set correctly
  - [ ] All vLLM arguments included (model, max-model-len, tensor-parallel-size, etc.)
  - [ ] Extra args from config.extra_args appended
  - [ ] Environment variables from config.environment added
  - [ ] Container labels added (llm-serve=true, model, runtime, gpus)
- **Technical Approach**:
  - Build command as list: ["podman", "run", "-d", ...]
  - Use uuid4().hex[:8] for unique container suffix
  - Port allocation: implement _next_port() helper (track in-memory)
  - GPU devices: iterate gpu list and add --device for each
  - Model path: join MODEL_PATH config with config.file_path
  - Labels: JSON serialize GPU list for label value
  - Follow example from architecture doc line 362-385
- **Files/Components**:
  - [ ] `dashboard/backend/services/container_command.py` - _generate_vllm method
  - [ ] `dashboard/backend/services/container_command.py` - _next_port helper
  - [ ] `dashboard/backend/services/container_command.py` - _container_name helper
  - [ ] `dashboard/backend/tests/test_container_command.py` - Test vLLM generation
- **Dependencies**: Task 3.1
- **Complexity**: L

#### Task 3.3: Implement GPU Device Mapping
- [ ] **Status**: Not Started
- **Description**: Create helper methods for GPU device mapping in nvidia-container-toolkit format
- **Acceptance Criteria**:
  - [ ] _format_gpu_devices method accepts list[int] and returns list of --device args
  - [ ] Correct format: --device nvidia.com/gpu=N for each GPU
  - [ ] Multiple GPUs result in multiple --device arguments
  - [ ] Empty GPU list raises ValueError
  - [ ] Unit tests cover single GPU, multi-GPU, and error cases
- **Technical Approach**:
  - Iterate GPU index list
  - For each GPU, append ["--device", f"nvidia.com/gpu={idx}"]
  - Validate list is not empty before processing
  - Return flat list of arguments ready to extend into command
- **Files/Components**:
  - [ ] `dashboard/backend/services/container_command.py` - _format_gpu_devices method
  - [ ] `dashboard/backend/tests/test_container_command.py` - GPU mapping tests
- **Dependencies**: Task 3.1
- **Complexity**: S

#### Task 3.4: Implement Environment Variable Building
- [ ] **Status**: Not Started
- **Description**: Create helper method to build environment variable arguments from config
- **Acceptance Criteria**:
  - [ ] _build_env_args method accepts config.environment dict and gpu list
  - [ ] CUDA_VISIBLE_DEVICES automatically added from GPU list
  - [ ] Config environment variables added as -e KEY=VALUE pairs
  - [ ] Returns list of ["-e", "KEY=VALUE", "-e", "KEY2=VALUE2", ...]
  - [ ] Handles empty environment dict gracefully
  - [ ] Unit tests verify correct formatting
- **Technical Approach**:
  - Start with base env: {"CUDA_VISIBLE_DEVICES": ",".join(str(g) for g in gpus)}
  - Merge config.environment into base env
  - Iterate merged dict and build ["-e", f"{k}={v}"] pairs
  - Return flat list ready to extend into command
- **Files/Components**:
  - [ ] `dashboard/backend/services/container_command.py` - _build_env_args method
  - [ ] `dashboard/backend/tests/test_container_command.py` - Environment tests
- **Dependencies**: Task 3.1
- **Complexity**: S

#### Task 3.5: Implement Container Labeling
- [ ] **Status**: Not Started
- **Description**: Create helper method to build container label arguments
- **Acceptance Criteria**:
  - [ ] _build_label_args method accepts config and GPU list
  - [ ] Labels include: llm-serve=true, model, runtime, gpus
  - [ ] GPU list JSON serialized for gpus label
  - [ ] Returns list of ["--label", "key=value", ...] pairs
  - [ ] All labels properly formatted for podman
  - [ ] Unit tests verify label formatting
- **Technical Approach**:
  - Define label dict with required keys
  - llm-serve: "true"
  - model: config.model_quant (derived from config relationships)
  - runtime: config.runtime
  - gpus: json.dumps(gpus)
  - Build list of ["--label", f"{k}={v}"] pairs
  - Return flat list ready to extend
- **Files/Components**:
  - [ ] `dashboard/backend/services/container_command.py` - _build_label_args method
  - [ ] `dashboard/backend/tests/test_container_command.py` - Label tests
- **Dependencies**: Task 3.1
- **Complexity**: S

#### Task 3.6: Implement Port Allocation
- [ ] **Status**: Not Started
- **Description**: Create port allocation mechanism to assign unique ports to containers
- **Acceptance Criteria**:
  - [ ] _next_port method returns next available port
  - [ ] Port range configurable (default 8001-8999)
  - [ ] Port tracking persists across container starts
  - [ ] Ports released when containers stop
  - [ ] Thread-safe allocation (use asyncio lock)
  - [ ] Unit tests verify no duplicate ports
- **Technical Approach**:
  - Maintain in-memory set of allocated ports
  - Start from configured base port (8001)
  - Increment until finding free port
  - Track port -> container_id mapping
  - Release port when container stops (called by daemon manager)
  - Use asyncio.Lock for thread safety
- **Files/Components**:
  - [ ] `dashboard/backend/services/container_command.py` - Port tracking logic
  - [ ] `dashboard/backend/services/container_command.py` - _next_port method
  - [ ] `dashboard/backend/services/container_command.py` - release_port method
  - [ ] `dashboard/backend/tests/test_container_command.py` - Port allocation tests
- **Dependencies**: Task 3.1
- **Complexity**: M

---

### 4. VRAM Calculations

#### Task 4.1: Implement VRAM Estimation Function
- [ ] **Status**: Not Started
- **Description**: Create utility function to estimate VRAM requirements for model+quantization
- **Acceptance Criteria**:
  - [ ] estimate_vram_gb function accepts parameter count and quantization
  - [ ] Formula implemented: VRAM = (params_billions * bits_per_param / 8) * 1.2
  - [ ] Quantization bits mapped correctly (fp16=16, awq=4, gptq=4, q4_k_m=4, q8=8)
  - [ ] Returns float representing GB required
  - [ ] Unit tests verify estimates match reference table from architecture
  - [ ] Helper function to parse parameter count from strings like "72B", "8B"
- **Technical Approach**:
  - Create utils/vram.py module
  - Map quantization names to bits per parameter
  - Parse parameter strings: regex to extract number, convert to billions
  - Apply formula with 1.2 overhead multiplier
  - Round to 1 decimal place for cleanliness
- **Files/Components**:
  - [ ] `dashboard/backend/utils/vram.py` - VRAM estimation functions
  - [ ] `dashboard/backend/tests/test_vram.py` - VRAM calculation tests
- **Dependencies**: None
- **Complexity**: S

#### Task 4.2: Implement Context Length VRAM Impact
- [ ] **Status**: Not Started
- **Description**: Create function to calculate additional VRAM needed for KV cache based on context length
- **Acceptance Criteria**:
  - [ ] calculate_kv_cache_gb function accepts model architecture params and context length
  - [ ] Formula based on: layers * heads * head_dim * 2 * context_length * batch_size * bytes
  - [ ] Returns float representing additional GB needed
  - [ ] Documented limitations (requires model architecture details)
  - [ ] Unit tests verify estimates for known models
- **Technical Approach**:
  - Implement formula from architecture doc line 445-447
  - Accept architecture params as dict (layers, heads, head_dim)
  - Default batch_size to 1 (conservative estimate)
  - Use 2 bytes for FP16 KV cache (common case)
  - Note: This is informational; not used for Phase 7 but useful for Phase 2
- **Files/Components**:
  - [ ] `dashboard/backend/utils/vram.py` - calculate_kv_cache_gb function
  - [ ] `dashboard/backend/tests/test_vram.py` - KV cache tests
- **Dependencies**: Task 4.1
- **Complexity**: S

---

### 5. Health Check Polling

#### Task 5.1: Implement Container Health Checker
- [ ] **Status**: Not Started
- **Description**: Create service to poll container health endpoints until ready
- **Acceptance Criteria**:
  - [ ] ContainerHealthChecker class created in services/
  - [ ] poll_until_ready async method accepts container endpoint and timeout
  - [ ] Polls /health endpoint at configured interval (default 1 second)
  - [ ] Returns True when health check succeeds (200 OK)
  - [ ] Raises TimeoutError if timeout exceeded
  - [ ] Logs each attempt with status
  - [ ] Configurable timeout and interval
- **Technical Approach**:
  - Use httpx.AsyncClient for HTTP requests
  - Implement exponential backoff or fixed interval (start with fixed)
  - Timeout based on model size (use timeout table from architecture)
  - Catch connection errors and retry
  - Log each attempt: "container_health_check", status=<code>, attempt=<n>
- **Files/Components**:
  - [ ] `dashboard/backend/services/health_check.py` - ContainerHealthChecker class
  - [ ] `dashboard/backend/tests/test_health_check.py` - Health check tests
- **Dependencies**: None (independent utility)
- **Complexity**: M

#### Task 5.2: Integrate Health Polling with ModelRouter
- [ ] **Status**: Not Started
- **Description**: Add health polling to ModelRouter.start_model flow
- **Acceptance Criteria**:
  - [ ] ModelRouter.start_model calls health checker after sending start command
  - [ ] Streams keepalive messages to client during health polling
  - [ ] Waits for health check success before routing request
  - [ ] Handles timeout errors gracefully (mark model as failed, retry)
  - [ ] Updates cluster state when model becomes healthy
  - [ ] Logs health check duration
- **Technical Approach**:
  - After daemon confirms container started, get container endpoint
  - Create health checker task: asyncio.create_task(health_checker.poll_until_ready(...))
  - While polling, yield keepalive to client (": keepalive\n\n")
  - On success, mark model as ready in cluster state
  - On timeout, mark model as failed, send stop command to daemon
- **Files/Components**:
  - [ ] `dashboard/backend/services/model_router.py` - Integrate health polling
  - [ ] `dashboard/backend/tests/test_model_router.py` - Test health integration
- **Dependencies**: Tasks 5.1, 6.1 (needs ModelRouter)
- **Complexity**: M

---

### 6. ModelRouter Integration

#### Task 6.1: Implement ModelRouter.ensure_capacity Method
- [ ] **Status**: Not Started
- **Description**: Add ensure_capacity method to identify and free GPU capacity for model loading
- **Acceptance Criteria**:
  - [ ] ensure_capacity method accepts GPURequirement spec
  - [ ] Identifies machines with sufficient free GPUs
  - [ ] Prefers single machine over multi-machine allocation
  - [ ] If insufficient capacity, selects LRU idle models for eviction
  - [ ] Returns list of Machine objects ready for allocation
  - [ ] Raises InsufficientCapacityError if cannot meet requirements
  - [ ] Marks machines as "busy" during allocation
  - [ ] Unit tests cover single-machine, multi-machine, and eviction scenarios
- **Technical Approach**:
  - Query cluster state for GPU availability per machine
  - Sort machines by free GPU count (prefer concentrated allocation)
  - Check single machine first, fall back to multi-machine
  - If still insufficient, call _find_eviction_candidates (LRU idle)
  - Evict models via evict_model method
  - Mark allocated GPUs as "reserved" until container starts
  - Return list of (machine, gpu_indices) tuples
- **Files/Components**:
  - [ ] `dashboard/backend/services/model_router.py` - ensure_capacity method
  - [ ] `dashboard/backend/services/model_router.py` - _find_eviction_candidates helper
  - [ ] `dashboard/backend/tests/test_model_router.py` - Capacity tests
- **Dependencies**: Assumes ModelRouter class exists from earlier phase
- **Complexity**: L

#### Task 6.2: Implement ModelRouter.start_model Method
- [ ] **Status**: Not Started
- **Description**: Add start_model method to orchestrate container startup
- **Acceptance Criteria**:
  - [ ] start_model method accepts model+quant identifier
  - [ ] Looks up launch config from database
  - [ ] Calls ensure_capacity to get machine allocation
  - [ ] Generates container command via ContainerCommandGenerator
  - [ ] Sends container.start command to daemon(s)
  - [ ] Waits for daemon acknowledgment
  - [ ] Polls health until ready (via health checker)
  - [ ] Updates cluster state with running container info
  - [ ] Returns container endpoint (host:port)
  - [ ] Handles errors at each step with rollback
- **Technical Approach**:
  - Query database for LaunchConfig matching model+quant
  - Call ensure_capacity with GPU requirements from config
  - For each allocated machine, generate command and send to daemon
  - Multi-machine: coordinate master/worker startup (master first)
  - Wait for all daemons to report container started
  - Poll health on master node (or single node)
  - On success, update cluster state and return endpoint
  - On failure, send stop commands and release capacity
- **Files/Components**:
  - [ ] `dashboard/backend/services/model_router.py` - start_model method
  - [ ] `dashboard/backend/tests/test_model_router.py` - Start model tests
- **Dependencies**: Tasks 3.2, 5.2, 6.1
- **Complexity**: XL

#### Task 6.3: Implement ModelRouter.evict_model Method
- [ ] **Status**: Not Started
- **Description**: Add evict_model method to stop and remove a running model
- **Acceptance Criteria**:
  - [ ] evict_model method accepts model+quant identifier
  - [ ] Verifies model is idle (queue empty, no in-flight requests)
  - [ ] Sends container.stop command to daemon(s)
  - [ ] Waits for daemon confirmation
  - [ ] Blocks queue during eviction (queue exists but rejects requests)
  - [ ] Releases GPU resources in cluster state
  - [ ] Releases port allocation
  - [ ] Logs eviction event
  - [ ] Unit tests verify idle check and multi-machine coordination
- **Technical Approach**:
  - Check QueueManager.is_idle(model_quant)
  - If not idle, raise ModelBusyError
  - Look up running container(s) from cluster state
  - Send stop command to each daemon hosting the model
  - Wait for all stops to confirm
  - Update cluster state: remove containers, free GPUs
  - Call port allocator to release port(s)
  - Log: "model_evicted", model=model_quant, reason="lru"
- **Files/Components**:
  - [ ] `dashboard/backend/services/model_router.py` - evict_model method
  - [ ] `dashboard/backend/tests/test_model_router.py` - Eviction tests
- **Dependencies**: Task 6.1
- **Complexity**: M

---

### 7. Initial vLLM Configurations (Seed Data)

#### Task 7.1: Create Seed Data SQL Script
- [ ] **Status**: Not Started
- **Description**: Create SQL script to populate database with initial vLLM configurations
- **Acceptance Criteria**:
  - [ ] SQL script created with INSERT statements for common models
  - [ ] At least 5 models included (Qwen 8B, 14B, 32B, 72B; Llama 8B)
  - [ ] Each model has 2-3 quantizations (e.g., awq, fp16, q4_k_m)
  - [ ] Launch configs defined with sensible defaults
  - [ ] VRAM requirements match reference table from architecture
  - [ ] Script is idempotent (uses INSERT ... ON CONFLICT or checks)
  - [ ] Script documented with comments
- **Technical Approach**:
  - Create db/seed_data/container_library.sql
  - Use transactions to ensure atomic insertion
  - Include models from architecture reference table (line 432-439)
  - Set is_default=TRUE for one launch config per quantization
  - Document where VRAM values came from (estimated vs measured)
- **Files/Components**:
  - [ ] `dashboard/backend/db/seed_data/container_library.sql` - Seed data script
  - [ ] `dashboard/backend/db/seed_data/README.md` - Documentation for seed data
- **Dependencies**: Task 1.1 (database schema must exist)
- **Complexity**: M

#### Task 7.2: Add Seed Data Loading to Startup
- [ ] **Status**: Not Started
- **Description**: Add option to load seed data on Dashboard first run or via CLI
- **Acceptance Criteria**:
  - [ ] CLI command to load seed data: `python -m backend.cli seed-container-library`
  - [ ] Checks if seed data already loaded (count rows, skip if present)
  - [ ] Loads SQL file and executes via SQLAlchemy connection
  - [ ] Logs success or skip message
  - [ ] Optional: Auto-load on first run if database empty
  - [ ] Unit tests verify seed data loads correctly
- **Technical Approach**:
  - Create backend/cli.py with click or argparse
  - Check model_configs table count, skip if > 0
  - Read SQL file and execute via session.execute()
  - Commit transaction on success
  - Log: "seed_data_loaded", table="container_library", models=<count>
- **Files/Components**:
  - [ ] `dashboard/backend/cli.py` - CLI tool for seed data
  - [ ] `dashboard/backend/tests/test_cli.py` - CLI tests
- **Dependencies**: Task 7.1
- **Complexity**: M

#### Task 7.3: Validate Seed Data Accuracy
- [ ] **Status**: Not Started
- **Description**: Create validation script to verify seed data VRAM estimates against known values
- **Acceptance Criteria**:
  - [ ] Validation script compares seed VRAM values to formula estimates
  - [ ] Reports any discrepancies > 10% difference
  - [ ] Outputs summary of all models and their VRAM requirements
  - [ ] Can be run as part of CI/testing
  - [ ] Documents known discrepancies (measured vs estimated)
- **Technical Approach**:
  - Query all quantization_configs from database
  - For each, calculate estimated VRAM using formula
  - Compare to stored vram_required_gb
  - Report differences with % variance
  - Flag any outliers for manual review
- **Files/Components**:
  - [ ] `dashboard/backend/scripts/validate_seed_vram.py` - Validation script
- **Dependencies**: Tasks 4.1, 7.1
- **Complexity**: S

---

### 8. API Endpoints for Container Configs

#### Task 8.1: Create Container Config List Endpoint
- [ ] **Status**: Not Started
- **Description**: Implement GET /api/containers endpoint to list all container configurations
- **Acceptance Criteria**:
  - [ ] Endpoint returns list of launch configs with nested model and quant info
  - [ ] Supports filtering by runtime (query param)
  - [ ] Supports filtering by model name (query param)
  - [ ] Returns Pydantic schema (LaunchConfigSchema)
  - [ ] Includes pagination support (limit/offset)
  - [ ] Unit tests verify filtering and pagination
- **Technical Approach**:
  - Query LaunchConfig with joined ModelConfig and QuantizationConfig
  - Apply filters from query params
  - Use SQLAlchemy selectin loading for relationships
  - Serialize to LaunchConfigSchema
  - Return JSON array
- **Files/Components**:
  - [ ] `dashboard/backend/api/control.py` - Add /api/containers endpoint
  - [ ] `dashboard/backend/tests/test_api_control.py` - API tests
- **Dependencies**: Tasks 2.4, 7.1
- **Complexity**: M

#### Task 8.2: Create Container Config Detail Endpoint
- [ ] **Status**: Not Started
- **Description**: Implement GET /api/containers/{id} endpoint to retrieve single config
- **Acceptance Criteria**:
  - [ ] Endpoint returns full launch config with all nested data
  - [ ] Returns 404 if config not found
  - [ ] Returns LaunchConfigSchema
  - [ ] Unit tests verify response structure
- **Technical Approach**:
  - Query LaunchConfig by ID with joined relationships
  - Return 404 if None
  - Serialize to LaunchConfigSchema
  - Return JSON object
- **Files/Components**:
  - [ ] `dashboard/backend/api/control.py` - Add /api/containers/{id} endpoint
  - [ ] `dashboard/backend/tests/test_api_control.py` - Detail endpoint tests
- **Dependencies**: Task 8.1
- **Complexity**: S

#### Task 8.3: Create Container Config Update Endpoint
- [ ] **Status**: Not Started
- **Description**: Implement PUT /api/containers/{id} endpoint to update launch configuration
- **Acceptance Criteria**:
  - [ ] Endpoint accepts LaunchConfigSchema (partial update)
  - [ ] Updates allowed fields: context_length, max_parallel, extra_args, environment
  - [ ] Rejects updates to runtime, gpu_count (structural changes)
  - [ ] Validates numeric fields (positive, within ranges)
  - [ ] Returns updated LaunchConfigSchema
  - [ ] Updates updated_at timestamp
  - [ ] Unit tests verify updates and validation errors
- **Technical Approach**:
  - Accept Pydantic model for update data
  - Query existing LaunchConfig
  - Apply updates to allowed fields only
  - Validate constraints (positive integers, etc.)
  - Commit and return updated object
  - Trigger updated_at via database trigger
- **Files/Components**:
  - [ ] `dashboard/backend/api/control.py` - Add PUT /api/containers/{id} endpoint
  - [ ] `dashboard/backend/tests/test_api_control.py` - Update tests
- **Dependencies**: Task 8.2
- **Complexity**: M

---

### 9. Integration Testing

#### Task 9.1: Create End-to-End Container Start Test
- [ ] **Status**: Not Started
- **Description**: Create integration test that verifies complete flow from API call to container start
- **Acceptance Criteria**:
  - [ ] Test creates launch config in database
  - [ ] Test calls ModelRouter.start_model
  - [ ] Verifies container command generated correctly
  - [ ] Mocks daemon communication and health checks
  - [ ] Verifies cluster state updated correctly
  - [ ] Verifies port allocated and returned
  - [ ] Test cleanup releases resources
- **Technical Approach**:
  - Use pytest fixtures to setup test database
  - Insert test launch config
  - Mock DaemonManager.send_command
  - Mock ContainerHealthChecker.poll_until_ready
  - Call start_model and verify command sent to daemon
  - Assert cluster state reflects running container
  - Cleanup: call evict_model
- **Files/Components**:
  - [ ] `dashboard/backend/tests/integration/test_container_lifecycle.py` - Integration test
- **Dependencies**: Tasks 3.2, 6.2
- **Complexity**: L

#### Task 9.2: Create Multi-GPU Container Test
- [ ] **Status**: Not Started
- **Description**: Create integration test for multi-GPU model startup
- **Acceptance Criteria**:
  - [ ] Test creates launch config requiring 2+ GPUs
  - [ ] Verifies ensure_capacity allocates multiple GPUs
  - [ ] Verifies container command includes all GPU devices
  - [ ] Verifies tensor_parallel setting correct
  - [ ] Verifies CUDA_VISIBLE_DEVICES includes all GPUs
  - [ ] Test covers single-machine multi-GPU case
- **Technical Approach**:
  - Insert launch config with gpu_count=2, tensor_parallel=2
  - Mock cluster state with machine having 2+ free GPUs
  - Call start_model
  - Verify command has two --device arguments
  - Verify CUDA_VISIBLE_DEVICES="0,1"
  - Verify --tensor-parallel-size 2 in vLLM args
- **Files/Components**:
  - [ ] `dashboard/backend/tests/integration/test_container_lifecycle.py` - Multi-GPU test
- **Dependencies**: Tasks 3.2, 6.2
- **Complexity**: L

#### Task 9.3: Create Eviction and Reload Test
- [ ] **Status**: Not Started
- **Description**: Create integration test for model eviction and subsequent reload
- **Acceptance Criteria**:
  - [ ] Test starts model, marks as idle, evicts
  - [ ] Verifies eviction releases GPU resources
  - [ ] Verifies port released
  - [ ] Test reloads same model
  - [ ] Verifies model loads on same or different GPU
  - [ ] Verifies new port allocated
- **Technical Approach**:
  - Start model A, verify running
  - Mark queue as idle (mock QueueManager)
  - Call evict_model(A)
  - Verify cluster state shows GPUs free
  - Start model A again
  - Verify successful start and potentially different port
- **Files/Components**:
  - [ ] `dashboard/backend/tests/integration/test_eviction.py` - Eviction test
- **Dependencies**: Tasks 6.2, 6.3
- **Complexity**: M

---

### 10. Documentation

#### Task 10.1: Document Container Command Generator
- [ ] **Status**: Not Started
- **Description**: Add comprehensive docstrings and usage examples for ContainerCommandGenerator
- **Acceptance Criteria**:
  - [ ] Class docstring explains purpose and usage
  - [ ] Each method has docstring with parameters and return value
  - [ ] Example usage provided in docstring
  - [ ] Type hints complete and accurate
  - [ ] Sphinx-compatible formatting
- **Technical Approach**:
  - Follow Google or NumPy docstring style
  - Include example code in module docstring
  - Document all parameters with types
  - Document exceptions raised
- **Files/Components**:
  - [ ] `dashboard/backend/services/container_command.py` - Add docstrings
- **Dependencies**: Tasks 3.1-3.6
- **Complexity**: S

#### Task 10.2: Document VRAM Calculation Functions
- [ ] **Status**: Not Started
- **Description**: Add documentation explaining VRAM estimation formulas and limitations
- **Acceptance Criteria**:
  - [ ] Module docstring explains estimation approach
  - [ ] Function docstrings include formula references
  - [ ] Limitations documented (estimates vs actual)
  - [ ] Reference table included as comment
  - [ ] Examples provided for common models
- **Technical Approach**:
  - Reference architecture doc formulas
  - Explain 1.2 overhead multiplier rationale
  - Note that actual usage may vary
  - Recommend monitoring and adjustment
- **Files/Components**:
  - [ ] `dashboard/backend/utils/vram.py` - Add documentation
- **Dependencies**: Tasks 4.1, 4.2
- **Complexity**: S

#### Task 10.3: Create Container Library User Guide
- [ ] **Status**: Not Started
- **Description**: Create user-facing documentation for container library feature
- **Acceptance Criteria**:
  - [ ] Markdown document explains container library concept
  - [ ] Instructions for viewing available configs
  - [ ] Instructions for updating configs via API
  - [ ] Example API calls with curl
  - [ ] Explanation of when to adjust context_length or max_parallel
  - [ ] Troubleshooting section for common issues
- **Technical Approach**:
  - Create docs/user-guide-container-library.md
  - Include screenshots (if UI exists) or API examples
  - Link to architecture doc for deep dive
  - Provide decision tree for config adjustments
- **Files/Components**:
  - [ ] `docs/user-guide-container-library.md` - User guide
- **Dependencies**: Tasks 8.1-8.3
- **Complexity**: M

---

## Summary

### Task Count by Category
- **Database Schema**: 2 tasks
- **SQLAlchemy Models**: 4 tasks
- **Container Command Generator**: 6 tasks
- **VRAM Calculations**: 2 tasks
- **Health Check Polling**: 2 tasks
- **ModelRouter Integration**: 3 tasks
- **Seed Data**: 3 tasks
- **API Endpoints**: 3 tasks
- **Integration Testing**: 3 tasks
- **Documentation**: 3 tasks

**Total Tasks**: 31

### Complexity Breakdown
- **Small (S)**: 9 tasks
- **Medium (M)**: 16 tasks
- **Large (L)**: 5 tasks
- **Extra Large (XL)**: 1 task

### Critical Path
1. Database migration (1.1) → SQLAlchemy models (2.1-2.3)
2. Command generator base (3.1) → vLLM generation (3.2)
3. ModelRouter integration (6.1-6.2)
4. Health checking (5.1-5.2)
5. Seed data (7.1-7.2)
6. Integration testing (9.1-9.3)

### Estimated Timeline
- **Database & Models**: 3-4 days
- **Command Generation**: 4-5 days
- **ModelRouter Integration**: 5-6 days
- **Health Checking & VRAM**: 2-3 days
- **Seed Data & APIs**: 3-4 days
- **Testing & Documentation**: 4-5 days

**Total Estimated Duration**: 21-27 days (3-4 weeks)

---

## Dependencies on Other Phases

**Prerequisites from Earlier Phases**:
- Database infrastructure (TimescaleDB, SQLAlchemy setup)
- ModelRouter class foundation (queue management)
- DaemonManager for sending commands
- ClusterState for tracking machine/GPU availability

**Enables Future Phases**:
- Phase 2: Model download and registration
- Phase 2: Container configuration UI
- Multi-machine coordination (future)

---

## Testing Strategy

1. **Unit Tests**: Each component tested in isolation with mocks
2. **Integration Tests**: End-to-end flows with test database
3. **Manual Testing**: Actual container starts on dev environment
4. **Validation**: Seed data VRAM estimates verified against formula

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| vLLM argument changes between versions | Pin vLLM version in config, document version compatibility |
| VRAM estimates inaccurate | Provide validation script, allow manual overrides |
| Port allocation conflicts | Implement proper locking, track allocations persistently |
| Health check timeouts too short | Use dynamic timeouts based on model size |
| Multi-GPU coordination failures | Start with single-GPU, add multi-GPU incrementally |

---

## Success Criteria

Phase 7 is complete when:
- [ ] Database schema created and populated with seed data
- [ ] vLLM commands generated correctly for single and multi-GPU configs
- [ ] Containers start successfully with proper GPU assignments
- [ ] Health checks poll until containers ready
- [ ] ModelRouter can trigger container starts and handle failures
- [ ] Container labels track all required metadata
- [ ] All unit and integration tests pass
- [ ] Documentation complete and accurate
