# Phase 3: Dashboard Backend - Implementation Plan

## Document Information
- **Phase**: 3 of 8
- **Phase Name**: Dashboard Backend
- **Related PRD**: [llms-prd.md](./llms-prd.md)
- **Related Architecture**: [architecture-dashboard.md](./architecture-dashboard.md)
- **Dependencies**: Phase 1 (Dev Environment Setup)
- **Created**: 2025-12-23
- **Status**: Not Started
- **Version**: 1.0

---

## Phase Overview

### Goal
Create FastAPI application with database schema and Control API skeleton that serves as the foundation for the Dashboard control plane.

### Deliverables
- FastAPI application structure with async support
- TimescaleDB schema with hypertables for metrics
- SQLAlchemy 2.0 models with async support
- Alembic migration setup
- Control API endpoints (placeholders returning mock data)
- Structured logging with structlog
- Configuration module with environment variable support

### Exit Criteria
- [ ] FastAPI app starts successfully with uvicorn
- [ ] Database connection established using asyncpg
- [ ] All tables created including TimescaleDB hypertables
- [ ] Control API endpoints return placeholder data with correct schemas
- [ ] Alembic migrations can be applied and rolled back
- [ ] Structured logging outputs JSON format
- [ ] Health check endpoint returns system status

### Out of Scope
- WebSocket handlers (Phase 4)
- Request Router logic (Phase 5)
- Frontend application (Phase 6)
- Actual container orchestration logic
- Authentication/authorization

---

## Task Breakdown

### Section 1: FastAPI Application Structure

#### Task 3.1: FastAPI Application Entry Point
- [ ] **Status**: Not Started
- **Description**: Create main FastAPI application with lifecycle management, CORS, and middleware setup
- **Acceptance Criteria**:
  - [ ] FastAPI app instantiates with proper metadata (title, version, description)
  - [ ] Application startup event initializes database connection pool
  - [ ] Application shutdown event closes database connections gracefully
  - [ ] CORS middleware configured for local network access (192.168.0.0/24)
  - [ ] Request ID middleware adds unique ID to each request
  - [ ] App can be started with uvicorn
- **Technical Approach**:
  - Use FastAPI's lifespan context manager for startup/shutdown
  - Configure CORS to allow local network (configurable via settings)
  - Add middleware for request logging and timing
  - Include OpenAPI documentation at /docs
- **Files/Components**:
  - [ ] `dashboard/backend/main.py` - FastAPI app instance and configuration
  - [ ] `dashboard/backend/__init__.py` - Package marker
- **Dependencies**: None
- **Complexity**: M

#### Task 3.2: Configuration Module
- [ ] **Status**: Not Started
- **Description**: Create configuration management using Pydantic settings with environment variable support
- **Acceptance Criteria**:
  - [ ] Settings class loads from environment variables with defaults
  - [ ] Database URL configurable (postgresql+asyncpg://...)
  - [ ] Server host, port configurable
  - [ ] Model storage path configurable
  - [ ] Logging level configurable
  - [ ] Encryption key for credentials validated as required
  - [ ] Settings validation fails fast on missing required values
- **Technical Approach**:
  - Use Pydantic BaseSettings for automatic env var loading
  - Provide sensible defaults for development
  - Use validator for encryption key format
  - Support .env file loading for development
- **Files/Components**:
  - [ ] `dashboard/backend/config.py` - Settings class with all configuration options
- **Dependencies**: None
- **Complexity**: S

#### Task 3.3: Structured Logging Setup
- [ ] **Status**: Not Started
- **Description**: Configure structlog for JSON structured logging throughout application
- **Acceptance Criteria**:
  - [ ] structlog configured with JSON output
  - [ ] Log entries include timestamp, level, event, and context fields
  - [ ] Logger available via `structlog.get_logger()`
  - [ ] Log levels configurable via environment variable
  - [ ] Request context (request_id) automatically included in logs
  - [ ] Example log entries demonstrate proper format
- **Technical Approach**:
  - Configure structlog with JSON processor
  - Add processors for timestamps, log levels, stack info
  - Integrate with FastAPI middleware for request context
  - Use contextvars for request ID propagation
- **Files/Components**:
  - [ ] `dashboard/backend/logging_config.py` - structlog configuration
  - [ ] `dashboard/backend/middleware.py` - Request logging middleware
- **Dependencies**: Task 3.1 (FastAPI app)
- **Complexity**: M

---

### Section 2: Database Setup and Session Management

#### Task 3.4: Database Session Management
- [ ] **Status**: Not Started
- **Description**: Configure async SQLAlchemy 2.0 session management with asyncpg driver and connection pooling
- **Acceptance Criteria**:
  - [ ] AsyncEngine created with asyncpg driver
  - [ ] AsyncSessionLocal factory configured
  - [ ] Connection pool settings appropriate for workload (pool_size=20, max_overflow=10)
  - [ ] get_db() dependency provides session per request
  - [ ] Sessions automatically closed after request
  - [ ] Database URL loaded from configuration
- **Technical Approach**:
  - Use create_async_engine with asyncpg
  - Configure connection pool with reasonable defaults
  - Create async_sessionmaker for session factory
  - Implement async context manager for database dependency
  - Add logging for connection pool statistics
- **Files/Components**:
  - [ ] `dashboard/backend/db/session.py` - Session management and database dependency
  - [ ] `dashboard/backend/db/__init__.py` - Package marker
- **Dependencies**: Task 3.2 (Configuration)
- **Complexity**: M

#### Task 3.5: SQLAlchemy Base and Mixins
- [ ] **Status**: Not Started
- **Description**: Create SQLAlchemy declarative base and common model mixins for timestamps
- **Acceptance Criteria**:
  - [ ] DeclarativeBase defined for all models
  - [ ] TimestampMixin provides created_at, updated_at columns
  - [ ] Mixins work with async SQLAlchemy
  - [ ] Base class available for import by all models
- **Technical Approach**:
  - Use SQLAlchemy 2.0 DeclarativeBase
  - Create TimestampMixin with TIMESTAMP columns and server defaults
  - Use mapped_column for type-safe column definitions
- **Files/Components**:
  - [ ] `dashboard/backend/db/base.py` - Base class and mixins
- **Dependencies**: Task 3.4 (Session management)
- **Complexity**: S

---

### Section 3: Database Models

#### Task 3.6: Machine Model
- [ ] **Status**: Not Started
- **Description**: Create SQLAlchemy model for machines table tracking registered GPU servers
- **Acceptance Criteria**:
  - [ ] Model includes: id (PK), hostname, ip_address, first_seen, last_seen, cpu_model, cpu_cores, memory_gb, notes
  - [ ] id field is TEXT (not auto-increment)
  - [ ] Timestamps with timezone support (TIMESTAMPTZ)
  - [ ] first_seen defaults to NOW() on insert
  - [ ] Model uses async-compatible patterns
- **Technical Approach**:
  - Use mapped_column with String, DateTime(timezone=True), Integer, Float types
  - Set server_default for first_seen
  - Make optional fields nullable
- **Files/Components**:
  - [ ] `dashboard/backend/models/database.py` - Start of database models file
  - [ ] `dashboard/backend/models/__init__.py` - Package marker
- **Dependencies**: Task 3.5 (Base class)
- **Complexity**: S

#### Task 3.7: Model and Model Quantization Models
- [ ] **Status**: Not Started
- **Description**: Create models for base LLMs and their quantization variants
- **Acceptance Criteria**:
  - [ ] Model table: id (SERIAL), name (UNIQUE), provider, huggingface_id, base_parameters, added_at
  - [ ] ModelQuantization table: id (SERIAL), model_id (FK), quantization, file_path, file_size_gb, vram_required_gb, gpu_count, added_at
  - [ ] Foreign key relationship from ModelQuantization to Model
  - [ ] Unique constraint on (model_id, quantization)
  - [ ] Proper SQLAlchemy relationship() defined
- **Technical Approach**:
  - Use relationship() with back_populates for bidirectional access
  - Set cascade options for deletions
  - Use CheckConstraint for gpu_count >= 1
- **Files/Components**:
  - [ ] `dashboard/backend/models/database.py` - Add Model and ModelQuantization classes
- **Dependencies**: Task 3.6 (Machine model)
- **Complexity**: M

#### Task 3.8: Container Config Model
- [ ] **Status**: Not Started
- **Description**: Create model for container runtime configurations per model+quantization
- **Acceptance Criteria**:
  - [ ] Table includes: id, model_quant_id (FK), runtime, context_length, max_parallel, tensor_parallel, pipeline_parallel, extra_args (JSONB), created_at, updated_at
  - [ ] Foreign key to model_quantizations
  - [ ] Runtime field defaults to 'vllm'
  - [ ] JSONB column for extra_args
  - [ ] TimestampMixin applied for created_at/updated_at
- **Technical Approach**:
  - Use JSON type for extra_args column
  - Set sensible defaults (context_length=8192, max_parallel=4, etc.)
  - Validate runtime is one of: vllm, sglang, llamacpp
- **Files/Components**:
  - [ ] `dashboard/backend/models/database.py` - Add ContainerConfig class
- **Dependencies**: Task 3.7 (Model Quantization)
- **Complexity**: S

#### Task 3.9: Credentials Model
- [ ] **Status**: Not Started
- **Description**: Create model for encrypted credential storage (HuggingFace tokens, etc.)
- **Acceptance Criteria**:
  - [ ] Table includes: id, name (UNIQUE), encrypted (BYTEA), created_at, updated_at
  - [ ] Name field indexed for fast lookup
  - [ ] Encrypted field is binary (LargeBinary in SQLAlchemy)
  - [ ] TimestampMixin applied
- **Technical Approach**:
  - Use LargeBinary type for encrypted field
  - Add unique index on name
  - Document that encryption/decryption happens in service layer
- **Files/Components**:
  - [ ] `dashboard/backend/models/database.py` - Add Credential class
- **Dependencies**: Task 3.8 (Container Config)
- **Complexity**: S

#### Task 3.10: Settings Model
- [ ] **Status**: Not Started
- **Description**: Create model for dynamic system settings stored as key-value pairs
- **Acceptance Criteria**:
  - [ ] Table includes: key (PK), value (JSONB), updated_at
  - [ ] Key is primary key (TEXT)
  - [ ] Value is JSONB for flexible storage
  - [ ] updated_at auto-updates on modification
- **Technical Approach**:
  - Use JSON type for value column
  - Set key as primary key
  - Use server_default for updated_at
- **Files/Components**:
  - [ ] `dashboard/backend/models/database.py` - Add Setting class
- **Dependencies**: Task 3.9 (Credentials)
- **Complexity**: S

---

### Section 4: TimescaleDB Hypertables

#### Task 3.11: CPU Stats Hypertable Model
- [ ] **Status**: Not Started
- **Description**: Create model for time-series CPU statistics with TimescaleDB hypertable configuration
- **Acceptance Criteria**:
  - [ ] Table includes: time (TIMESTAMPTZ), machine_id (TEXT), cores (INTEGER), load_percent (REAL)
  - [ ] Composite primary key: (time, machine_id)
  - [ ] Model annotation for hypertable creation via migration
  - [ ] Index on machine_id for queries
- **Technical Approach**:
  - Use DateTime(timezone=True) for time column
  - Mark as hypertable using comment or table args
  - Primary key includes time dimension
- **Files/Components**:
  - [ ] `dashboard/backend/models/database.py` - Add CPUStat class
- **Dependencies**: Task 3.10 (Settings)
- **Complexity**: M

#### Task 3.12: GPU Stats Hypertable Model
- [ ] **Status**: Not Started
- **Description**: Create model for time-series GPU statistics with detailed metrics per GPU
- **Acceptance Criteria**:
  - [ ] Table includes: time, machine_id, gpu_uuid, gpu_index, gpu_name, memory_total_gb, memory_used_gb, utilization, temperature_c, model_loaded
  - [ ] Composite primary key: (time, machine_id, gpu_uuid)
  - [ ] Model annotation for hypertable creation
  - [ ] Indexes on machine_id and gpu_uuid
- **Technical Approach**:
  - Include all fields from architecture doc schema
  - Use appropriate numeric types (Float for GB, Integer for percentages)
  - Make model_loaded nullable (TEXT)
- **Files/Components**:
  - [ ] `dashboard/backend/models/database.py` - Add GPUStat class
- **Dependencies**: Task 3.11 (CPU Stats)
- **Complexity**: M

#### Task 3.13: Memory Stats Hypertable Model
- [ ] **Status**: Not Started
- **Description**: Create model for time-series system memory statistics
- **Acceptance Criteria**:
  - [ ] Table includes: time, machine_id, total_gb, used_gb, available_gb
  - [ ] Composite primary key: (time, machine_id)
  - [ ] Model annotation for hypertable creation
  - [ ] Index on machine_id
- **Technical Approach**:
  - Use Float type for GB values
  - Match schema from architecture doc exactly
- **Files/Components**:
  - [ ] `dashboard/backend/models/database.py` - Add MemoryStat class
- **Dependencies**: Task 3.12 (GPU Stats)
- **Complexity**: S

---

### Section 5: Pydantic Schemas

#### Task 3.14: Machine Schemas
- [ ] **Status**: Not Started
- **Description**: Create Pydantic schemas for Machine API requests/responses
- **Acceptance Criteria**:
  - [ ] MachineBase with common fields
  - [ ] MachineResponse with all fields including computed properties
  - [ ] MachineListResponse with summary info
  - [ ] Schemas use proper Python types (datetime, Optional, etc.)
  - [ ] ConfigDict with from_attributes=True for ORM mode
- **Technical Approach**:
  - Inherit from BaseModel
  - Use Pydantic v2 patterns (ConfigDict)
  - Add computed fields for status (online/offline)
- **Files/Components**:
  - [ ] `dashboard/backend/models/schemas.py` - Start of schemas file
- **Dependencies**: Task 3.6 (Machine model)
- **Complexity**: M

#### Task 3.15: Model and Container Schemas
- [ ] **Status**: Not Started
- **Description**: Create Pydantic schemas for models, quantizations, and container configs
- **Acceptance Criteria**:
  - [ ] ModelBase, ModelResponse with quantizations nested
  - [ ] QuantizationBase, QuantizationResponse
  - [ ] ContainerConfigBase, ContainerConfigResponse
  - [ ] All relationships properly typed
  - [ ] Validation for enum fields (runtime)
- **Technical Approach**:
  - Use nested schemas for relationships
  - Add validators for runtime enum
  - Include computed fields for model+quant identifier
- **Files/Components**:
  - [ ] `dashboard/backend/models/schemas.py` - Add model-related schemas
- **Dependencies**: Task 3.14 (Machine schemas)
- **Complexity**: M

#### Task 3.16: Stats Schemas
- [ ] **Status**: Not Started
- **Description**: Create Pydantic schemas for statistics API responses
- **Acceptance Criteria**:
  - [ ] CPUStatsResponse for CPU metrics
  - [ ] GPUStatsResponse for GPU metrics
  - [ ] MemoryStatsResponse for memory metrics
  - [ ] ClusterStatusResponse for overall cluster state
  - [ ] Proper timestamp handling
- **Technical Approach**:
  - Match stat fields from database models
  - Use datetime for timestamps
  - Add aggregation schemas for cluster-wide stats
- **Files/Components**:
  - [ ] `dashboard/backend/models/schemas.py` - Add stats schemas
- **Dependencies**: Task 3.15 (Model schemas)
- **Complexity**: S

---

### Section 6: Alembic Migrations

#### Task 3.17: Alembic Setup
- [ ] **Status**: Not Started
- **Description**: Initialize Alembic for database migrations with async support
- **Acceptance Criteria**:
  - [ ] `alembic init` completed in dashboard/backend/db/migrations
  - [ ] alembic.ini configured with sqlalchemy.url from environment
  - [ ] env.py configured for async migrations
  - [ ] env.py imports all models for autogenerate
  - [ ] Migrations can run with `alembic upgrade head`
- **Technical Approach**:
  - Use alembic init to create migration directory
  - Modify env.py to use asyncio and asyncpg
  - Import all models in env.py for metadata
  - Configure target_metadata from Base.metadata
- **Files/Components**:
  - [ ] `dashboard/backend/db/migrations/alembic.ini` - Alembic configuration
  - [ ] `dashboard/backend/db/migrations/env.py` - Migration environment
  - [ ] `dashboard/backend/db/migrations/versions/` - Migration versions directory
- **Dependencies**: Task 3.13 (All models defined)
- **Complexity**: M

#### Task 3.18: Initial Migration - Regular Tables
- [ ] **Status**: Not Started
- **Description**: Create initial migration for all regular (non-hypertable) tables
- **Acceptance Criteria**:
  - [ ] Migration creates: machines, models, model_quantizations, container_configs, credentials, settings
  - [ ] All constraints (PK, FK, UNIQUE) included
  - [ ] Indexes created as specified
  - [ ] Migration can be applied to empty database
  - [ ] Migration can be rolled back cleanly
- **Technical Approach**:
  - Use `alembic revision --autogenerate` to generate migration
  - Review and edit generated migration for correctness
  - Test upgrade and downgrade operations
- **Files/Components**:
  - [ ] `dashboard/backend/db/migrations/versions/001_initial_tables.py` - Initial migration
- **Dependencies**: Task 3.17 (Alembic setup)
- **Complexity**: M

#### Task 3.19: TimescaleDB Extension and Hypertables Migration
- [ ] **Status**: Not Started
- **Description**: Create migration to enable TimescaleDB extension and convert stats tables to hypertables
- **Acceptance Criteria**:
  - [ ] Migration creates: cpu_stats, gpu_stats, memory_stats tables
  - [ ] `CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;` executed
  - [ ] Tables converted to hypertables using `SELECT create_hypertable(...)`
  - [ ] Retention policies set (30 days default)
  - [ ] Migration includes proper upgrade/downgrade
- **Technical Approach**:
  - Use op.execute() for raw SQL commands
  - Create tables first, then convert to hypertables
  - Set chunk_time_interval appropriately (1 day)
  - Add retention policy using add_retention_policy()
- **Files/Components**:
  - [ ] `dashboard/backend/db/migrations/versions/002_timescaledb_hypertables.py` - Hypertable migration
- **Dependencies**: Task 3.18 (Initial migration)
- **Complexity**: L

---

### Section 7: Control API Endpoints

#### Task 3.20: Health Check Endpoint
- [ ] **Status**: Not Started
- **Description**: Create health check endpoint that returns system status including database connectivity
- **Acceptance Criteria**:
  - [ ] GET /health returns 200 when healthy
  - [ ] Response includes: status, database_connected, version
  - [ ] Database connectivity checked with simple query
  - [ ] Endpoint does not require authentication
  - [ ] Logs health check failures
- **Technical Approach**:
  - Use FastAPI route with no dependencies
  - Execute simple SELECT 1 query to verify DB connection
  - Catch exceptions and return 503 if unhealthy
  - Include app version from config
- **Files/Components**:
  - [ ] `dashboard/backend/api/__init__.py` - Package marker
  - [ ] `dashboard/backend/api/health.py` - Health endpoint
- **Dependencies**: Task 3.4 (Database session)
- **Complexity**: S

#### Task 3.21: Cluster Status Endpoint
- [ ] **Status**: Not Started
- **Description**: Create endpoint to return cluster overview (placeholder data)
- **Acceptance Criteria**:
  - [ ] GET /api/cluster/status returns cluster summary
  - [ ] Response includes: total_machines, online_machines, total_gpus, free_gpus, running_models
  - [ ] Returns placeholder/mock data for now
  - [ ] Schema matches ClusterStatusResponse
  - [ ] Endpoint logged and timed
- **Technical Approach**:
  - Create placeholder service that returns mock data
  - Use proper response schema
  - Add TODO comments for Phase 4 integration
- **Files/Components**:
  - [ ] `dashboard/backend/api/control.py` - Control API endpoints
  - [ ] `dashboard/backend/services/__init__.py` - Services package marker
  - [ ] `dashboard/backend/services/cluster_state.py` - Cluster state service (stub)
- **Dependencies**: Task 3.16 (Stats schemas)
- **Complexity**: M

#### Task 3.22: Machine List and Detail Endpoints
- [ ] **Status**: Not Started
- **Description**: Create endpoints to list machines and get individual machine details
- **Acceptance Criteria**:
  - [ ] GET /api/machines returns list of all machines
  - [ ] GET /api/machines/{id} returns detailed machine info
  - [ ] Queries database for machine records
  - [ ] Returns 404 if machine not found
  - [ ] Includes placeholder GPU stats (actual stats in Phase 4)
  - [ ] Responses use MachineResponse schema
- **Technical Approach**:
  - Query machines table with SQLAlchemy
  - Use async session from dependency
  - Return ORM models converted to Pydantic schemas
  - Handle not found with HTTPException
- **Files/Components**:
  - [ ] `dashboard/backend/api/control.py` - Add machine endpoints
  - [ ] `dashboard/backend/services/machine_service.py` - Machine service
- **Dependencies**: Task 3.21 (Cluster status)
- **Complexity**: M

#### Task 3.23: Model List Endpoint
- [ ] **Status**: Not Started
- **Description**: Create endpoint to list available models with their quantizations
- **Acceptance Criteria**:
  - [ ] GET /api/models returns all models with nested quantizations
  - [ ] Eager loads quantizations and container configs
  - [ ] Response uses ModelResponse schema
  - [ ] Results ordered by name
  - [ ] Query optimized to avoid N+1
- **Technical Approach**:
  - Use selectinload for relationship eager loading
  - Query models with quantizations joined
  - Convert to Pydantic schemas with nested data
- **Files/Components**:
  - [ ] `dashboard/backend/api/control.py` - Add model list endpoint
  - [ ] `dashboard/backend/services/model_service.py` - Model service
- **Dependencies**: Task 3.22 (Machine endpoints)
- **Complexity**: M

#### Task 3.24: Container Config Endpoints
- [ ] **Status**: Not Started
- **Description**: Create endpoints to list and retrieve container configurations
- **Acceptance Criteria**:
  - [ ] GET /api/containers returns all container configs
  - [ ] GET /api/containers/{id} returns specific config
  - [ ] Includes related model and quantization info
  - [ ] Returns 404 if config not found
  - [ ] Response uses ContainerConfigResponse schema
- **Technical Approach**:
  - Query container_configs with joins to models and quantizations
  - Use eager loading for relationships
  - Convert to response schemas
- **Files/Components**:
  - [ ] `dashboard/backend/api/control.py` - Add container config endpoints
  - [ ] `dashboard/backend/services/container_service.py` - Container service (stub)
- **Dependencies**: Task 3.23 (Model endpoints)
- **Complexity**: S

#### Task 3.25: Logs Endpoint
- [ ] **Status**: Not Started
- **Description**: Create endpoint to retrieve system logs with filtering (placeholder implementation)
- **Acceptance Criteria**:
  - [ ] GET /api/logs returns recent log entries
  - [ ] Supports query params: level, limit, offset
  - [ ] Returns placeholder log data for now
  - [ ] Response includes: timestamp, level, event, context
  - [ ] Documented TODO for file-based log retrieval
- **Technical Approach**:
  - Return mock log entries matching expected format
  - Add query parameter validation
  - Document future implementation (read from log files)
- **Files/Components**:
  - [ ] `dashboard/backend/api/control.py` - Add logs endpoint
- **Dependencies**: Task 3.24 (Container config endpoints)
- **Complexity**: S

#### Task 3.26: Settings Endpoints
- [ ] **Status**: Not Started
- **Description**: Create endpoints to get and update system settings
- **Acceptance Criteria**:
  - [ ] GET /api/settings returns all settings as key-value pairs
  - [ ] GET /api/settings/{key} returns specific setting
  - [ ] PUT /api/settings/{key} updates setting value
  - [ ] Returns 404 if setting not found
  - [ ] Validates JSON value structure
  - [ ] Updates updated_at timestamp
- **Technical Approach**:
  - Query settings table
  - Use JSONB column for flexible value storage
  - Validate JSON before storing
  - Return settings as dict
- **Files/Components**:
  - [ ] `dashboard/backend/api/control.py` - Add settings endpoints
  - [ ] `dashboard/backend/services/settings_service.py` - Settings service
- **Dependencies**: Task 3.25 (Logs endpoint)
- **Complexity**: M

---

### Section 8: Integration and Testing

#### Task 3.27: API Router Integration
- [ ] **Status**: Not Started
- **Description**: Integrate all API routers into main FastAPI application
- **Acceptance Criteria**:
  - [ ] All routers included in main app with proper prefixes
  - [ ] /health mounted at root level
  - [ ] /api/cluster/*, /api/machines/*, etc. all accessible
  - [ ] OpenAPI docs include all endpoints
  - [ ] Tags applied for organization
- **Technical Approach**:
  - Use app.include_router() for each router
  - Apply prefixes (/api, /health)
  - Add tags for Swagger grouping
- **Files/Components**:
  - [ ] `dashboard/backend/main.py` - Update to include all routers
- **Dependencies**: Task 3.26 (Settings endpoints)
- **Complexity**: S

#### Task 3.28: Database Initialization Script
- [ ] **Status**: Not Started
- **Description**: Create script to initialize database and run migrations
- **Acceptance Criteria**:
  - [ ] Script creates database if not exists
  - [ ] Runs alembic migrations to latest
  - [ ] Seeds with initial data (optional settings)
  - [ ] Can be run idempotently
  - [ ] Logs progress and errors
- **Technical Approach**:
  - Use asyncpg to create database if needed
  - Shell out to alembic commands or use alembic API
  - Add seed data for common settings
- **Files/Components**:
  - [ ] `dashboard/backend/scripts/init_db.py` - Database init script
  - [ ] `dashboard/backend/scripts/__init__.py` - Package marker
- **Dependencies**: Task 3.19 (Migrations)
- **Complexity**: M

#### Task 3.29: Manual Testing Verification
- [ ] **Status**: Not Started
- **Description**: Perform manual testing of all implemented functionality
- **Acceptance Criteria**:
  - [ ] FastAPI app starts without errors
  - [ ] Health check returns 200
  - [ ] All Control API endpoints accessible
  - [ ] Database queries execute successfully
  - [ ] Logging outputs JSON to stdout
  - [ ] Swagger docs display all endpoints correctly
  - [ ] Alembic migrations apply and rollback cleanly
- **Technical Approach**:
  - Start uvicorn with app
  - Use curl or httpie to test each endpoint
  - Review logs for proper formatting
  - Test migration up/down
  - Verify database schema with psql
- **Files/Components**:
  - [ ] Manual test checklist (in this document)
- **Dependencies**: Task 3.27 (Router integration), Task 3.28 (DB init)
- **Complexity**: M

#### Task 3.30: Documentation and README
- [ ] **Status**: Not Started
- **Description**: Document how to run the dashboard backend and verify functionality
- **Acceptance Criteria**:
  - [ ] README includes: how to build container, how to run, environment variables
  - [ ] Database setup instructions documented
  - [ ] Example API requests included
  - [ ] Troubleshooting section added
- **Technical Approach**:
  - Create dashboard/README.md
  - Document all environment variables
  - Provide example curl commands
  - Add common issues and solutions
- **Files/Components**:
  - [ ] `dashboard/README.md` - Dashboard documentation
- **Dependencies**: Task 3.29 (Testing)
- **Complexity**: S

---

## Task Summary

### By Section
| Section | Task Count | Complexity |
|---------|-----------|------------|
| 1. FastAPI Application Structure | 3 | S(1), M(2) |
| 2. Database Setup and Session Management | 3 | S(1), M(2) |
| 3. Database Models | 5 | S(4), M(1) |
| 4. TimescaleDB Hypertables | 3 | S(1), M(2) |
| 5. Pydantic Schemas | 3 | S(1), M(2) |
| 6. Alembic Migrations | 3 | M(2), L(1) |
| 7. Control API Endpoints | 7 | S(3), M(4) |
| 8. Integration and Testing | 3 | S(1), M(2) |

### Total Tasks: 30

### Complexity Breakdown
- **Small (S)**: 11 tasks
- **Medium (M)**: 18 tasks
- **Large (L)**: 1 task
- **Extra Large (XL)**: 0 tasks

### Estimated Effort
- Small tasks: ~2-4 hours each = 22-44 hours
- Medium tasks: ~4-8 hours each = 72-144 hours
- Large tasks: ~8-16 hours each = 8-16 hours
- **Total estimated range**: 102-204 hours

---

## Dependencies Graph

```
Task 3.1 (FastAPI App)
  └── Task 3.2 (Configuration)
        ├── Task 3.3 (Logging)
        └── Task 3.4 (DB Session)
              └── Task 3.5 (Base & Mixins)
                    └── Task 3.6 (Machine Model)
                          └── Task 3.7 (Model/Quant Models)
                                └── Task 3.8 (Container Config)
                                      └── Task 3.9 (Credentials)
                                            └── Task 3.10 (Settings)
                                                  └── Task 3.11 (CPU Stats)
                                                        └── Task 3.12 (GPU Stats)
                                                              └── Task 3.13 (Memory Stats)
                                                                    ├── Task 3.14 (Machine Schemas)
                                                                    │     └── Task 3.15 (Model Schemas)
                                                                    │           └── Task 3.16 (Stats Schemas)
                                                                    └── Task 3.17 (Alembic Setup)
                                                                          └── Task 3.18 (Initial Migration)
                                                                                └── Task 3.19 (Hypertables Migration)

Task 3.16 (Stats Schemas) + Task 3.4 (DB Session)
  └── Task 3.20 (Health Check)
        └── Task 3.21 (Cluster Status)
              └── Task 3.22 (Machine Endpoints)
                    └── Task 3.23 (Model Endpoints)
                          └── Task 3.24 (Container Endpoints)
                                └── Task 3.25 (Logs Endpoint)
                                      └── Task 3.26 (Settings Endpoints)
                                            └── Task 3.27 (Router Integration)

Task 3.19 (Migrations) + Task 3.27 (Router Integration)
  └── Task 3.28 (DB Init Script)
        └── Task 3.29 (Manual Testing)
              └── Task 3.30 (Documentation)
```

---

## Risk Assessment

### High Risk
- **TimescaleDB hypertable setup**: First time integrating TimescaleDB; may encounter issues with extension installation or hypertable conversion
  - *Mitigation*: Test TimescaleDB separately first; have fallback to regular PostgreSQL tables if needed
- **Async SQLAlchemy 2.0**: Newer async patterns may have gotchas
  - *Mitigation*: Follow official SQLAlchemy 2.0 async documentation closely; test early

### Medium Risk
- **Connection pool tuning**: May need adjustment for actual workload
  - *Mitigation*: Start with conservative defaults; monitor and adjust in later phases
- **Migration rollback**: Complex migrations may be hard to roll back
  - *Mitigation*: Test migrations thoroughly; keep migrations small and focused

### Low Risk
- **Pydantic schemas**: Well-established patterns
- **FastAPI setup**: Standard configuration
- **Structured logging**: Straightforward with structlog

---

## Testing Strategy

### Manual Testing (Phase 3)
- Start FastAPI app and verify it serves
- Test each endpoint with curl/httpie
- Verify database schema created correctly
- Test migrations up and down
- Check log output format

### Automated Testing (Future)
- Unit tests for Pydantic schemas and validation
- Integration tests for database queries
- API endpoint tests with test database
- Migration tests with temporary database

---

## Key Files Reference

### Configuration Files
- `dashboard/backend/config.py` - All environment variable configuration
- `dashboard/backend/db/migrations/alembic.ini` - Alembic configuration

### Core Application
- `dashboard/backend/main.py` - FastAPI application entry point
- `dashboard/backend/logging_config.py` - Structured logging setup
- `dashboard/backend/middleware.py` - Request middleware

### Database Layer
- `dashboard/backend/db/session.py` - Database session management
- `dashboard/backend/db/base.py` - SQLAlchemy base and mixins
- `dashboard/backend/models/database.py` - All SQLAlchemy models
- `dashboard/backend/models/schemas.py` - All Pydantic schemas

### API Layer
- `dashboard/backend/api/health.py` - Health check endpoint
- `dashboard/backend/api/control.py` - All Control API endpoints

### Services Layer
- `dashboard/backend/services/cluster_state.py` - Cluster state management (stub)
- `dashboard/backend/services/machine_service.py` - Machine operations
- `dashboard/backend/services/model_service.py` - Model operations
- `dashboard/backend/services/container_service.py` - Container operations (stub)
- `dashboard/backend/services/settings_service.py` - Settings operations

### Database Migrations
- `dashboard/backend/db/migrations/env.py` - Alembic environment
- `dashboard/backend/db/migrations/versions/001_initial_tables.py` - Initial migration
- `dashboard/backend/db/migrations/versions/002_timescaledb_hypertables.py` - Hypertables

### Scripts
- `dashboard/backend/scripts/init_db.py` - Database initialization

---

## Environment Variables Reference

```bash
# Required
LLM_SERVE_ENCRYPTION_KEY=your-secret-key-here-min-32-chars

# Database (defaults shown)
DATABASE_URL=postgresql+asyncpg://llmserve:llmserve@localhost:5432/llmserve
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Server
HOST=0.0.0.0
PORT=8080

# Network
ALLOWED_NETWORKS=192.168.0.0/24

# Storage
MODEL_PATH=/data/projects/ai/models

# Metrics
METRICS_RETENTION_DAYS=30

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## Success Metrics

Phase 3 is complete when:
1. All 30 tasks marked as complete
2. FastAPI app starts without errors
3. All database tables created including hypertables
4. All Control API endpoints return expected responses (even if placeholder)
5. Alembic migrations apply and rollback successfully
6. Structured logging outputs JSON format
7. Health check endpoint confirms database connectivity
8. Documentation complete and accurate

---

## Notes

- This phase establishes the foundation for all future Dashboard work
- Focus on correct async patterns - they will be reused throughout
- TimescaleDB hypertables are critical for Phase 5+ performance
- Placeholder data in Control API will be replaced in Phase 4 with real daemon data
- Consider using database container for development (PostgreSQL + TimescaleDB)
