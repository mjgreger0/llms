# Phase 1: Dev Environment Setup - Detailed Implementation Plan

## Document Information
- **Phase**: 1 of 8
- **Related Documents**:
  - [Implementation Overview](./implementation-overview.md)
  - [PRD](./llms-prd.md)
  - [Architecture Overview](./architecture-overview.md)
  - [Dashboard Architecture](./architecture-dashboard.md)
  - [Daemon Architecture](./architecture-daemon.md)
- **Created**: 2025-12-23
- **Status**: Complete
- **Completed**: 2025-12-23

---

## Phase Overview

**Goal**: Establish project structure and production-ready container configurations

**Scope**: This phase creates the foundational structure for the entire project. We build production-ready Containerfiles for both Dashboard and Daemon components, establish the directory structure, configure Python and Node.js dependencies, and create minimal entrypoints to validate that containers can build and start successfully.

**Exit Criteria**:
- [x] Both Dashboard and Daemon containers build successfully
- [x] Containers start and pass basic health checks
- [x] Directory structure matches architecture specifications
- [x] All dependency manifests configured correctly

---

## Progress Tracking

**Overall Phase Progress**: 31/31 tasks completed (100%)

### Section Progress
- **Section 1 - Directory Structure**: 6/6 tasks (100%)
- **Section 2 - Dashboard Containerfile**: 7/7 tasks (100%)
- **Section 3 - Daemon Containerfile**: 4/4 tasks (100%)
- **Section 4 - Python Dependencies**: 6/6 tasks (100%)
- **Section 5 - Frontend Dependencies**: 3/3 tasks (100%)
- **Section 6 - Basic Entrypoints**: 4/4 tasks (100%)
- **Section 7 - Validation**: 1/1 tasks (100%)

---

## Section 1: Directory Structure Creation

#### Task 1.1: Create Root Project Structure
- [x] **Status**: Complete
- **Description**: Create the top-level directory structure for the entire LLM Serve project
- **Acceptance Criteria**:
  - [x] Root `llms/` directory exists (already present)
  - [x] `docs/` directory contains all architecture documents
  - [x] `dashboard/`, `daemon/`, and `containers/` directories created
- **Technical Approach**:
  - Verify existing docs directory structure
  - Create missing top-level directories
  - Ensure directory structure matches PRD specification (Section: Development Requirements)
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/dashboard/` - Dashboard component directory
  - [x] `/data/home/mgreger/proj/llms/daemon/` - Daemon component directory
  - [x] `/data/home/mgreger/proj/llms/containers/` - Container library reference configs
- **Dependencies**: None
- **Complexity**: S

---

#### Task 1.2: Create Dashboard Directory Structure
- [x] **Status**: Complete
- **Description**: Create complete directory structure for Dashboard component including backend and frontend
- **Acceptance Criteria**:
  - [x] Backend directories match architecture specification
  - [x] Frontend directories follow SvelteKit conventions
  - [x] Database migration directory exists
- **Technical Approach**:
  - Follow structure from architecture-dashboard.md (Section: Application Structure)
  - Create backend directories: api/, services/, models/, db/
  - Create frontend directories: src/routes/, src/lib/
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/dashboard/backend/` - Backend Python code
  - [x] `/data/home/mgreger/proj/llms/dashboard/backend/api/` - API endpoints
  - [x] `/data/home/mgreger/proj/llms/dashboard/backend/services/` - Business logic
  - [x] `/data/home/mgreger/proj/llms/dashboard/backend/models/` - Data models
  - [x] `/data/home/mgreger/proj/llms/dashboard/backend/db/` - Database code
  - [x] `/data/home/mgreger/proj/llms/dashboard/backend/db/migrations/` - Alembic migrations
  - [x] `/data/home/mgreger/proj/llms/dashboard/frontend/` - SvelteKit app
  - [x] `/data/home/mgreger/proj/llms/dashboard/frontend/src/` - Frontend source
  - [x] `/data/home/mgreger/proj/llms/dashboard/frontend/src/routes/` - SvelteKit routes
  - [x] `/data/home/mgreger/proj/llms/dashboard/frontend/src/lib/` - Shared components
  - [x] `/data/home/mgreger/proj/llms/dashboard/frontend/static/` - Static assets
- **Dependencies**: Task 1.1
- **Complexity**: S

---

#### Task 1.3: Create Daemon Directory Structure
- [x] **Status**: Complete
- **Description**: Create complete directory structure for Daemon component
- **Acceptance Criteria**:
  - [x] Source directories match architecture specification
  - [x] Service module structure supports stats collection and container management
- **Technical Approach**:
  - Follow structure from architecture-daemon.md (Section: Application Structure)
  - Create modular structure for different daemon responsibilities
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/` - Daemon source code
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/` - Service modules
  - [x] `/data/home/mgreger/proj/llms/daemon/src/models/` - Data models
  - [x] `/data/home/mgreger/proj/llms/daemon/src/protocol/` - JSON-RPC protocol
- **Dependencies**: Task 1.1
- **Complexity**: S

---

#### Task 1.4: Create Container Library Structure
- [x] **Status**: Complete
- **Description**: Create directory structure for container configuration references
- **Acceptance Criteria**:
  - [x] Runtime directories created for vLLM, SGLang, llama.cpp
  - [x] Structure supports adding reference configurations later
- **Technical Approach**:
  - Create placeholder directories for different runtimes
  - Reference configs will be populated in Phase 7
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/containers/vllm/` - vLLM reference configs
  - [x] `/data/home/mgreger/proj/llms/containers/sglang/` - SGLang reference configs
  - [x] `/data/home/mgreger/proj/llms/containers/llamacpp/` - llama.cpp reference configs
- **Dependencies**: Task 1.1
- **Complexity**: S

---

#### Task 1.5: Create Python Package __init__.py Files
- [x] **Status**: Complete
- **Description**: Add __init__.py files to make Python directories into packages
- **Acceptance Criteria**:
  - [x] All Python module directories have __init__.py
  - [x] Files are empty (no content needed for now)
- **Technical Approach**:
  - Touch __init__.py in all backend and daemon subdirectories
  - Ensures Python can import modules correctly
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/dashboard/backend/__init__.py`
  - [x] `/data/home/mgreger/proj/llms/dashboard/backend/api/__init__.py`
  - [x] `/data/home/mgreger/proj/llms/dashboard/backend/services/__init__.py`
  - [x] `/data/home/mgreger/proj/llms/dashboard/backend/models/__init__.py`
  - [x] `/data/home/mgreger/proj/llms/dashboard/backend/db/__init__.py`
  - [x] `/data/home/mgreger/proj/llms/daemon/src/__init__.py`
  - [x] `/data/home/mgreger/proj/llms/daemon/src/services/__init__.py`
  - [x] `/data/home/mgreger/proj/llms/daemon/src/models/__init__.py`
  - [x] `/data/home/mgreger/proj/llms/daemon/src/protocol/__init__.py`
- **Dependencies**: Tasks 1.2, 1.3
- **Complexity**: S

---

#### Task 1.6: Create .gitignore Files
- [x] **Status**: Complete
- **Description**: Add .gitignore files to prevent committing build artifacts and dependencies
- **Acceptance Criteria**:
  - [x] Root .gitignore covers Python and Node.js artifacts
  - [x] Dashboard frontend .gitignore covers SvelteKit build outputs
  - [x] Common patterns included: __pycache__, node_modules, .env, build/
- **Technical Approach**:
  - Create comprehensive .gitignore at project root
  - Add frontend-specific .gitignore in dashboard/frontend/
  - Include common Python, Node.js, and editor patterns
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/.gitignore` - Root gitignore
  - [x] `/data/home/mgreger/proj/llms/dashboard/frontend/.gitignore` - Frontend-specific
- **Dependencies**: Tasks 1.1, 1.2
- **Complexity**: S

---

## Section 2: Dashboard Containerfile

#### Task 2.1: Create Multi-Stage Dashboard Containerfile
- [x] **Status**: Complete
- **Description**: Create production-ready Containerfile with frontend build stage and Python runtime stage
- **Acceptance Criteria**:
  - [x] Stage 1: Node.js 20 environment for frontend build
  - [x] Stage 2: Python 3.11 runtime with TimescaleDB client
  - [x] Frontend static assets copied from build stage to runtime stage
  - [x] Container exposes port 8080
- **Technical Approach**:
  - Use multi-stage build pattern: frontend-builder -> python-runtime
  - Frontend stage: Node 20, npm ci, SvelteKit build with adapter-static
  - Runtime stage: Python 3.11-slim, install dependencies, copy backend + static files
  - Reference architecture-dashboard.md (Section: Deployment)
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/dashboard/Containerfile` - Multi-stage Containerfile
- **Dependencies**: Task 1.2
- **Complexity**: M

---

#### Task 2.2: Configure Dashboard Frontend Build Stage
- [x] **Status**: Complete
- **Description**: Implement Node.js build stage for SvelteKit application
- **Acceptance Criteria**:
  - [x] Uses node:20-slim base image
  - [x] Copies package.json and package-lock.json first (layer caching)
  - [x] Runs npm install for dependency installation
  - [x] Runs npm run build to generate static output
  - [x] Build artifacts in /app/build directory
- **Technical Approach**:
  - FROM node:20-slim AS frontend-builder
  - WORKDIR /app
  - COPY frontend/package*.json ./
  - RUN npm install
  - COPY frontend/ ./
  - RUN npm run build
- **Files/Components**:
  - [x] Frontend build stage in `/data/home/mgreger/proj/llms/dashboard/Containerfile`
- **Dependencies**: Task 2.1
- **Complexity**: M

---

#### Task 2.3: Configure Dashboard Python Runtime Stage
- [x] **Status**: Complete
- **Description**: Implement Python runtime stage with TimescaleDB support
- **Acceptance Criteria**:
  - [x] Uses python:3.11-slim base image
  - [x] Installs system dependencies for asyncpg (PostgreSQL client)
  - [x] Creates /app working directory
  - [x] Installs Python dependencies from pyproject.toml
  - [x] Cleans up apt cache to minimize image size
- **Technical Approach**:
  - FROM python:3.11-slim
  - Install libpq-dev for asyncpg (RUN apt-get update && apt-get install -y libpq-dev)
  - WORKDIR /app
  - COPY pyproject.toml ./
  - RUN pip install --no-cache-dir .
  - Clean up: rm -rf /var/lib/apt/lists/*
- **Files/Components**:
  - [x] Python runtime stage in `/data/home/mgreger/proj/llms/dashboard/Containerfile`
- **Dependencies**: Task 2.1
- **Complexity**: M

---

#### Task 2.4: Copy Dashboard Code and Assets
- [x] **Status**: Complete
- **Description**: Copy backend code and built frontend assets into runtime container
- **Acceptance Criteria**:
  - [x] Backend code copied to /app/backend
  - [x] Built frontend assets copied from builder stage to /app/static
  - [x] Directory structure matches runtime expectations
- **Technical Approach**:
  - COPY backend/ ./backend/
  - COPY --from=frontend-builder /app/build ./static/
  - Ensures backend can serve static files from ./static/
- **Files/Components**:
  - [x] COPY directives in `/data/home/mgreger/proj/llms/dashboard/Containerfile`
- **Dependencies**: Tasks 2.2, 2.3
- **Complexity**: S

---

#### Task 2.5: Configure Dashboard Container Volumes
- [x] **Status**: Complete
- **Description**: Define volume mount points for persistent data
- **Acceptance Criteria**:
  - [x] VOLUME directives for /data/config, /data/db, /data/logs
  - [x] Documentation comments explain each volume purpose
- **Technical Approach**:
  - Add VOLUME directives to Containerfile
  - /data/config - Container definitions, settings (persistent)
  - /data/db - TimescaleDB data (persistent)
  - /data/logs - Application logs (persistent)
  - Reference architecture-overview.md (Section: Deployment Topology)
- **Files/Components**:
  - [x] VOLUME directives in `/data/home/mgreger/proj/llms/dashboard/Containerfile`
- **Dependencies**: Task 2.3
- **Complexity**: S

---

#### Task 2.6: Set Dashboard Container Entrypoint
- [x] **Status**: Complete
- **Description**: Define container startup command
- **Acceptance Criteria**:
  - [x] CMD directive runs uvicorn with backend.main:app
  - [x] Listens on 0.0.0.0:8080
  - [x] No --reload flag (production mode)
- **Technical Approach**:
  - CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
  - Production configuration (no hot reload)
- **Files/Components**:
  - [x] CMD directive in `/data/home/mgreger/proj/llms/dashboard/Containerfile`
- **Dependencies**: Task 2.3
- **Complexity**: S

---

#### Task 2.7: Add Dashboard Container Labels
- [x] **Status**: Complete
- **Description**: Add metadata labels to container image
- **Acceptance Criteria**:
  - [x] org.opencontainers.image labels for metadata
  - [x] Labels include: title, description, version, component
- **Technical Approach**:
  - LABEL org.opencontainers.image.title="LLM Serve Dashboard"
  - LABEL org.opencontainers.image.description="Centralized control plane for LLM cluster"
  - LABEL org.opencontainers.image.version="0.1.0"
  - LABEL component="dashboard"
- **Files/Components**:
  - [x] LABEL directives in `/data/home/mgreger/proj/llms/dashboard/Containerfile`
- **Dependencies**: Task 2.1
- **Complexity**: S

---

## Section 3: Daemon Containerfile

#### Task 3.1: Create Daemon Containerfile
- [x] **Status**: Complete
- **Description**: Create production-ready Containerfile for GPU Daemon
- **Acceptance Criteria**:
  - [x] Uses python:3.11-slim base image
  - [x] Includes dependencies for pynvml GPU monitoring
  - [x] Container runs as single-stage build (no frontend)
  - [x] Exposes necessary host mounts in documentation
- **Technical Approach**:
  - Single-stage build (daemon has no frontend)
  - FROM python:3.11-slim
  - Install system dependencies if needed
  - Install Python packages from pyproject.toml
  - Copy source code
  - Reference architecture-daemon.md (Section: Deployment)
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/Containerfile` - Daemon Containerfile
- **Dependencies**: Task 1.3
- **Complexity**: M

---

#### Task 3.2: Configure Daemon Python Environment
- [x] **Status**: Complete
- **Description**: Set up Python environment with required dependencies
- **Acceptance Criteria**:
  - [x] Python 3.11 base image
  - [x] System dependencies for pynvml installed if needed
  - [x] pip install from pyproject.toml with --no-cache-dir
  - [x] /app working directory created
- **Technical Approach**:
  - WORKDIR /app
  - COPY pyproject.toml ./
  - RUN pip install --no-cache-dir .
  - pynvml requires NVIDIA drivers accessible from container (runtime mount)
- **Files/Components**:
  - [x] Python environment setup in `/data/home/mgreger/proj/llms/daemon/Containerfile`
- **Dependencies**: Task 3.1
- **Complexity**: M

---

#### Task 3.3: Copy Daemon Source Code
- [x] **Status**: Complete
- **Description**: Copy daemon source code into container
- **Acceptance Criteria**:
  - [x] src/ directory copied to /app/src
  - [x] All Python modules accessible for import
- **Technical Approach**:
  - COPY src/ ./src/
  - Maintains src/ directory structure
- **Files/Components**:
  - [x] COPY directive in `/data/home/mgreger/proj/llms/daemon/Containerfile`
- **Dependencies**: Task 3.2
- **Complexity**: S

---

#### Task 3.4: Set Daemon Container Entrypoint and Labels
- [x] **Status**: Complete
- **Description**: Define startup command and metadata labels
- **Acceptance Criteria**:
  - [x] CMD runs Python main module
  - [x] Container metadata labels added
  - [x] Documentation comments explain required runtime mounts
- **Technical Approach**:
  - CMD ["python", "-m", "src.main"]
  - Add LABEL directives for metadata
  - Document required mounts in comments:
    - -v /proc:/host/proc:ro
    - -v /sys:/host/sys:ro
    - -v /run/podman/podman.sock:/run/podman/podman.sock
    - --device nvidia.com/gpu=all
- **Files/Components**:
  - [x] CMD and LABEL directives in `/data/home/mgreger/proj/llms/daemon/Containerfile`
- **Dependencies**: Task 3.2
- **Complexity**: S

---

## Section 4: Python Dependencies (pyproject.toml)

#### Task 4.1: Create Dashboard pyproject.toml
- [x] **Status**: Complete
- **Description**: Define Python dependencies and project metadata for Dashboard
- **Acceptance Criteria**:
  - [x] Project metadata: name, version, description
  - [x] Core dependencies: fastapi, uvicorn, asyncpg, sqlalchemy, pydantic
  - [x] WebSocket and HTTP client: websockets, httpx
  - [x] Database and security: alembic, cryptography
  - [x] Logging: structlog
  - [x] Uses PEP 621 format
- **Technical Approach**:
  - Create pyproject.toml with [project] section
  - Dependencies from architecture-dashboard.md (Section: Technology Stack)
  - Version constraints: fastapi>=0.104, uvicorn[standard]>=0.24, etc.
  - Optional dev dependencies: pytest, ruff
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/dashboard/pyproject.toml` - Dashboard Python config
- **Dependencies**: Task 1.2
- **Complexity**: M

---

#### Task 4.2: Create Daemon pyproject.toml
- [x] **Status**: Complete
- **Description**: Define Python dependencies and project metadata for Daemon
- **Acceptance Criteria**:
  - [x] Project metadata: name, version, description
  - [x] Core dependencies: fastapi, uvicorn, websockets
  - [x] System monitoring: pynvml, psutil
  - [x] Container management: podman (v5.0+)
  - [x] Utilities: structlog, pydantic
- **Technical Approach**:
  - Create pyproject.toml with [project] section
  - Dependencies from architecture-daemon.md (Section: Technology Stack)
  - Version constraints: pynvml>=11.5, psutil>=5.9, podman>=5.0
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/pyproject.toml` - Daemon Python config
- **Dependencies**: Task 1.3
- **Complexity**: M

---

#### Task 4.3: Configure Dashboard Build System
- [x] **Status**: Complete
- **Description**: Add build system configuration to Dashboard pyproject.toml
- **Acceptance Criteria**:
  - [x] [build-system] section with setuptools backend
  - [x] [tool.setuptools] section for package discovery
  - [x] Packages include backend module
- **Technical Approach**:
  - [build-system]
  - requires = ["setuptools>=61.0"]
  - build-backend = "setuptools.build_meta"
  - [tool.setuptools]
  - packages = ["backend"]
- **Files/Components**:
  - [x] Build system config in `/data/home/mgreger/proj/llms/dashboard/pyproject.toml`
- **Dependencies**: Task 4.1
- **Complexity**: S

---

#### Task 4.4: Configure Daemon Build System
- [x] **Status**: Complete
- **Description**: Add build system configuration to Daemon pyproject.toml
- **Acceptance Criteria**:
  - [x] [build-system] section with setuptools backend
  - [x] [tool.setuptools] section for package discovery
  - [x] Packages include src module
- **Technical Approach**:
  - [build-system]
  - requires = ["setuptools>=61.0"]
  - build-backend = "setuptools.build_meta"
  - [tool.setuptools]
  - packages = ["src"]
- **Files/Components**:
  - [x] Build system config in `/data/home/mgreger/proj/llms/daemon/pyproject.toml`
- **Dependencies**: Task 4.2
- **Complexity**: S

---

#### Task 4.5: Add Dashboard Optional Dependencies
- [x] **Status**: Complete
- **Description**: Define optional development dependencies for Dashboard
- **Acceptance Criteria**:
  - [x] [project.optional-dependencies] section with dev group
  - [x] Dev dependencies: pytest, pytest-asyncio, ruff, mypy
  - [x] Can install with pip install .[dev]
- **Technical Approach**:
  - [project.optional-dependencies]
  - dev = ["pytest>=7.4", "pytest-asyncio>=0.21", "ruff>=0.1", "mypy>=1.7"]
  - Supports development workflow
- **Files/Components**:
  - [x] Optional dependencies in `/data/home/mgreger/proj/llms/dashboard/pyproject.toml`
- **Dependencies**: Task 4.1
- **Complexity**: S

---

#### Task 4.6: Add Daemon Optional Dependencies
- [x] **Status**: Complete
- **Description**: Define optional development dependencies for Daemon
- **Acceptance Criteria**:
  - [x] [project.optional-dependencies] section with dev group
  - [x] Dev dependencies: pytest, pytest-asyncio, ruff
- **Technical Approach**:
  - [project.optional-dependencies]
  - dev = ["pytest>=7.4", "pytest-asyncio>=0.21", "ruff>=0.1"]
- **Files/Components**:
  - [x] Optional dependencies in `/data/home/mgreger/proj/llms/daemon/pyproject.toml`
- **Dependencies**: Task 4.2
- **Complexity**: S

---

## Section 5: Frontend Dependencies (package.json)

#### Task 5.1: Create Frontend package.json
- [x] **Status**: Complete
- **Description**: Define Node.js dependencies for SvelteKit frontend
- **Acceptance Criteria**:
  - [x] Package metadata: name, version, type: module
  - [x] Scripts: dev, build, preview
  - [x] Core dependencies: @sveltejs/kit, svelte
  - [x] Build adapter: @sveltejs/adapter-static
  - [x] Dev tools: vite, typescript (if using TS)
- **Technical Approach**:
  - Create package.json in dashboard/frontend/
  - Dependencies from architecture-dashboard.md (Section: Technology Stack)
  - Scripts:
    - "dev": "vite dev"
    - "build": "vite build"
    - "preview": "vite preview"
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/dashboard/frontend/package.json` - Frontend config
- **Dependencies**: Task 1.2
- **Complexity**: M

---

#### Task 5.2: Create SvelteKit Configuration
- [x] **Status**: Complete
- **Description**: Create svelte.config.js for SvelteKit settings
- **Acceptance Criteria**:
  - [x] Imports @sveltejs/adapter-static
  - [x] Configures adapter for static build
  - [x] Output directory: build/
- **Technical Approach**:
  - import adapter from '@sveltejs/adapter-static';
  - export default { kit: { adapter: adapter() } };
  - Static build generates pre-rendered HTML/JS/CSS
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/dashboard/frontend/svelte.config.js` - SvelteKit config
- **Dependencies**: Task 5.1
- **Complexity**: S

---

#### Task 5.3: Create Vite Configuration
- [x] **Status**: Complete
- **Description**: Create vite.config.js for build tool settings
- **Acceptance Criteria**:
  - [x] Imports sveltekit plugin
  - [x] Basic configuration for development and production
- **Technical Approach**:
  - import { sveltekit } from '@sveltejs/kit/vite';
  - export default { plugins: [sveltekit()] };
  - Minimal config, defaults work for Phase 1
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/dashboard/frontend/vite.config.js` - Vite config
- **Dependencies**: Task 5.1
- **Complexity**: S

---

## Section 6: Basic Entrypoints and Health Checks

#### Task 6.1: Create Dashboard Backend Entrypoint
- [x] **Status**: Complete
- **Description**: Create minimal FastAPI application stub for Dashboard
- **Acceptance Criteria**:
  - [x] backend/main.py creates FastAPI app instance
  - [x] /health endpoint returns 200 OK
  - [x] Can start with uvicorn backend.main:app
- **Technical Approach**:
  - from fastapi import FastAPI
  - app = FastAPI(title="LLM Serve Dashboard")
  - @app.get("/health")
  - async def health(): return {"status": "ok"}
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/dashboard/backend/main.py` - FastAPI app entrypoint
- **Dependencies**: Tasks 1.2, 4.1
- **Complexity**: S

---

#### Task 6.2: Create Daemon Main Entrypoint
- [x] **Status**: Complete
- **Description**: Create minimal main entry point for Daemon
- **Acceptance Criteria**:
  - [x] src/main.py has main() function
  - [x] Prints startup message and exits cleanly
  - [x] Can run with python -m src.main
- **Technical Approach**:
  - import asyncio
  - async def main():
  -     print("LLM Serve Daemon starting...")
  - if __name__ == "__main__":
  -     asyncio.run(main())
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/daemon/src/main.py` - Daemon entrypoint
- **Dependencies**: Tasks 1.3, 4.2
- **Complexity**: S

---

#### Task 6.3: Create Frontend Minimal Layout
- [x] **Status**: Complete
- **Description**: Create minimal SvelteKit application structure
- **Acceptance Criteria**:
  - [x] src/routes/+page.svelte with placeholder content
  - [x] src/app.html with basic HTML template
  - [x] App builds with npm run build
- **Technical Approach**:
  - Create +page.svelte with <h1>LLM Serve Dashboard</h1>
  - Create app.html with %sveltekit.head% and %sveltekit.body%
  - Minimal structure to validate build pipeline
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/dashboard/frontend/src/routes/+page.svelte` - Home page
  - [x] `/data/home/mgreger/proj/llms/dashboard/frontend/src/app.html` - HTML template
- **Dependencies**: Tasks 1.2, 5.1
- **Complexity**: S

---

#### Task 6.4: Create Docker Ignore Files
- [x] **Status**: Complete
- **Description**: Add .dockerignore files to optimize container builds
- **Acceptance Criteria**:
  - [x] Dashboard .dockerignore excludes node_modules, __pycache__, .git
  - [x] Daemon .dockerignore excludes __pycache__, .git, tests
  - [x] Reduces build context size and speeds up builds
- **Technical Approach**:
  - Create .dockerignore in dashboard/ and daemon/ directories
  - Exclude: node_modules, __pycache__, *.pyc, .git, .env, *.log
  - Frontend-specific: .svelte-kit, build
- **Files/Components**:
  - [x] `/data/home/mgreger/proj/llms/dashboard/.dockerignore` - Dashboard ignore patterns
  - [x] `/data/home/mgreger/proj/llms/daemon/.dockerignore` - Daemon ignore patterns
- **Dependencies**: Tasks 1.2, 1.3
- **Complexity**: S

---

## Section 7: Build and Validation

#### Task 7.1: Build and Test Containers
- [x] **Status**: Complete
- **Description**: Build both containers and validate they start successfully
- **Acceptance Criteria**:
  - [x] Dashboard container builds without errors
  - [x] Daemon container builds without errors
  - [x] Dashboard container starts and /health returns 200
  - [x] Daemon container starts and prints startup message
  - [x] Both containers can be stopped cleanly
- **Technical Approach**:
  - Build Dashboard: `podman build -t llm-serve-dashboard:latest dashboard/`
  - Build Daemon: `podman build -t llm-serve-daemon:latest daemon/`
  - Test Dashboard: `podman run --rm -p 8080:8080 llm-serve-dashboard:latest`
  - Verify health: `curl http://localhost:8080/health`
  - Test Daemon: `podman run --rm llm-serve-daemon:latest` (should start then exit)
- **Files/Components**:
  - Build validation for both containers
- **Dependencies**: All previous tasks
- **Complexity**: M

---

## Technical Decisions and Notes

### Containerfile Multi-Stage Build
**Decision**: Use multi-stage build for Dashboard to separate frontend build from runtime
**Rationale**:
- Reduces final image size (no Node.js in runtime)
- Separates build-time from runtime dependencies
- Follows Docker/Podman best practices
**Trade-offs**: Slightly more complex Containerfile, but better production image

### TimescaleDB Deployment
**Decision**: TimescaleDB will be embedded in Dashboard container (Phase 1), external deployment later
**Rationale**:
- Simplifies initial setup and testing
- Single container easier to manage during development
- Can migrate to external TimescaleDB in future phases
**Trade-offs**: Data persistence requires volume mounts, container restart loses connections

### Python Package Management
**Decision**: Use pyproject.toml (PEP 621) instead of setup.py or requirements.txt
**Rationale**:
- Modern Python standard
- Single source of truth for dependencies
- Better integration with build tools
**Trade-offs**: None, this is the recommended approach

### Frontend Build Tool
**Decision**: Use Vite (comes with SvelteKit) instead of Webpack
**Rationale**:
- Default for SvelteKit
- Faster builds and HMR
- Better DX
**Trade-offs**: None, Vite is superior for modern frontend

### Static Site Generation
**Decision**: Use @sveltejs/adapter-static to pre-render frontend
**Rationale**:
- FastAPI can serve static files easily
- No need for Node.js runtime in production
- Better security (no server-side JS)
**Trade-offs**: Dynamic routes require special handling, but we don't need them in Phase 1

---

## Dependencies Between Tasks

```
Section 1 (Directory Structure)
  1.1 → 1.2, 1.3, 1.4, 1.6
  1.2 → 1.5, 2.1, 4.1, 5.1, 6.1, 6.3
  1.3 → 1.5, 3.1, 4.2, 6.2

Section 2 (Dashboard Containerfile)
  2.1 → 2.2, 2.3, 2.7
  2.2, 2.3 → 2.4
  2.3 → 2.5, 2.6

Section 3 (Daemon Containerfile)
  3.1 → 3.2
  3.2 → 3.3, 3.4

Section 4 (Python Dependencies)
  4.1 → 4.3, 4.5, 6.1
  4.2 → 4.4, 4.6, 6.2

Section 5 (Frontend Dependencies)
  5.1 → 5.2, 5.3, 6.3

Section 6 (Entrypoints)
  All → 7.1
```

---

## Validation Checklist

Before marking this phase complete, verify:

- [x] Directory structure matches architecture documents
- [x] Dashboard Containerfile builds successfully
- [x] Daemon Containerfile builds successfully
- [x] Dashboard container starts and /health endpoint accessible
- [x] Daemon container starts and logs startup message
- [x] All pyproject.toml files have correct dependencies
- [x] Frontend package.json has correct dependencies
- [x] Frontend builds successfully (npm run build)
- [x] .gitignore files prevent committing build artifacts
- [x] All __init__.py files created for Python packages
- [x] No errors in build output
- [x] Containers can be stopped cleanly

---

## Next Phase

Once Phase 1 is complete, proceed to **Phase 2: Daemon Core** which will implement:
- Stats collection (CPU, memory, GPU via pynvml)
- Container management (Podman integration)
- Health monitoring
- Configuration via environment variables

Phase 2 reference: [implementation-phase-2-daemon-core.md](./implementation-phase-2-daemon-core.md)
