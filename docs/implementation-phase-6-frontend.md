# Phase 6: Dashboard Frontend - Implementation Plan

## Document Information
- **Phase**: 6 - Dashboard Frontend
- **Dependencies**: Phase 5 (Dashboard Backend API)
- **Created**: 2025-12-23
- **Status**: Ready for Implementation

---

## Phase Overview

**Goal**: Build SvelteKit UI for cluster monitoring and testing

**Deliverables**:
- SvelteKit project structure with adapter-static
- Cluster Overview page (machines, GPUs, running models)
- Machine Detail page (per-machine stats, GPU details)
- Chat/Test interface (send requests, streaming responses)
- Logs page (system logs)
- API client library
- WebSocket store for real-time updates
- Static build integration with FastAPI

**Exit Criteria**:
- All 4 pages functional
- Real-time updates working
- Static build served by FastAPI
- Chat can send requests and display streaming responses

---

## Task Breakdown

### 1. Project Initialization

#### Task 1.1: SvelteKit Project Setup
- [ ] **Status**: Not Started
- **Description**: Initialize SvelteKit project with TypeScript support and adapter-static for static site generation
- **Acceptance Criteria**:
  - [ ] SvelteKit project created with TypeScript
  - [ ] adapter-static installed and configured
  - [ ] vite.config.js configured for development
  - [ ] Package.json with all required dependencies
  - [ ] Project builds successfully to static files
- **Technical Approach**:
  - Use `npm create svelte@latest` in dashboard/frontend directory
  - Install `@sveltejs/adapter-static`
  - Configure svelte.config.js to use adapter-static
  - Set up build output to `build/` directory
  - Configure fallback for SPA mode (fallback: 'index.html')
- **Files/Components**:
  - [ ] `dashboard/frontend/package.json` - dependencies and scripts
  - [ ] `dashboard/frontend/svelte.config.js` - SvelteKit configuration
  - [ ] `dashboard/frontend/vite.config.js` - Vite bundler config
  - [ ] `dashboard/frontend/tsconfig.json` - TypeScript configuration
  - [ ] `dashboard/frontend/src/app.d.ts` - TypeScript types
  - [ ] `dashboard/frontend/src/app.html` - HTML template
- **Dependencies**: None
- **Complexity**: S

#### Task 1.2: Configure Build Integration
- [ ] **Status**: Not Started
- **Description**: Set up npm scripts and ensure static build output is compatible with FastAPI serving
- **Acceptance Criteria**:
  - [ ] `npm run dev` starts dev server
  - [ ] `npm run build` creates static files in build/
  - [ ] Build output includes index.html and all assets
  - [ ] Asset paths are relative (not absolute)
  - [ ] Build process completes without errors
- **Technical Approach**:
  - Configure adapter-static with `{ pages: 'build', assets: 'build' }`
  - Set base path to '' for relative URLs
  - Add npm scripts: dev, build, preview
  - Verify output structure matches FastAPI static serving expectations
- **Files/Components**:
  - [ ] `dashboard/frontend/package.json` - scripts section
  - [ ] `dashboard/frontend/svelte.config.js` - adapter-static config
- **Dependencies**: Task 1.1
- **Complexity**: S

#### Task 1.3: Install Frontend Dependencies
- [ ] **Status**: Not Started
- **Description**: Install all required npm packages for UI development
- **Acceptance Criteria**:
  - [ ] All dependencies installed successfully
  - [ ] No security vulnerabilities
  - [ ] package-lock.json generated
  - [ ] Dependencies documented in package.json
- **Technical Approach**:
  - Install core: svelte, @sveltejs/kit, @sveltejs/adapter-static
  - Install dev tools: typescript, vite, prettier
  - Install utilities: date-fns (date formatting), marked (markdown rendering)
  - No heavy UI frameworks - keep it lightweight
- **Files/Components**:
  - [ ] `dashboard/frontend/package.json` - dependencies
  - [ ] `dashboard/frontend/package-lock.json` - locked versions
- **Dependencies**: Task 1.1
- **Complexity**: S

---

### 2. Core Infrastructure

#### Task 2.1: API Client Library
- [ ] **Status**: Not Started
- **Description**: Create TypeScript API client for backend communication
- **Acceptance Criteria**:
  - [ ] Type-safe API client with all endpoints
  - [ ] Error handling for network failures
  - [ ] Request/response type definitions
  - [ ] Support for JSON parsing
  - [ ] Configurable base URL
- **Technical Approach**:
  - Create class-based API client using fetch
  - Define TypeScript interfaces for all request/response types
  - Implement methods for each API endpoint (GET /api/cluster/status, etc.)
  - Add error handling with typed exceptions
  - Export singleton instance for use in components
- **Files/Components**:
  - [ ] `dashboard/frontend/src/lib/api/client.ts` - API client class
  - [ ] `dashboard/frontend/src/lib/api/types.ts` - TypeScript types
  - [ ] `dashboard/frontend/src/lib/api/index.ts` - exports
- **Dependencies**: Task 1.1
- **Complexity**: M

#### Task 2.2: WebSocket Store for Real-Time Updates
- [ ] **Status**: Not Started
- **Description**: Create Svelte store that connects to /ws/ui and pushes cluster state updates
- **Acceptance Criteria**:
  - [ ] WebSocket connection to /ws/ui endpoint
  - [ ] Automatic reconnection on disconnect
  - [ ] Svelte store updated with cluster state changes
  - [ ] Components can subscribe to state updates
  - [ ] Connection status observable (connected/disconnected)
- **Technical Approach**:
  - Create custom Svelte writable store
  - Implement WebSocket connection with reconnection logic
  - Parse incoming messages and update store
  - Expose connection state for UI feedback
  - Handle browser lifecycle (page visibility)
- **Files/Components**:
  - [ ] `dashboard/frontend/src/lib/stores/cluster.ts` - cluster state store
  - [ ] `dashboard/frontend/src/lib/stores/websocket.ts` - WebSocket connection management
- **Dependencies**: Task 1.1
- **Complexity**: L

#### Task 2.3: Utility Functions
- [ ] **Status**: Not Started
- **Description**: Create utility functions for formatting, validation, and common operations
- **Acceptance Criteria**:
  - [ ] Format bytes to human-readable (GB, TB)
  - [ ] Format percentages
  - [ ] Format timestamps/dates
  - [ ] GPU status helpers (free/used/total)
  - [ ] Model name parsing utilities
- **Technical Approach**:
  - Create pure functions for each utility
  - Add TypeScript types for all parameters
  - Export from centralized utils module
  - Include unit tests (optional but recommended)
- **Files/Components**:
  - [ ] `dashboard/frontend/src/lib/utils/format.ts` - formatting functions
  - [ ] `dashboard/frontend/src/lib/utils/gpu.ts` - GPU-specific helpers
  - [ ] `dashboard/frontend/src/lib/utils/index.ts` - exports
- **Dependencies**: Task 1.1
- **Complexity**: S

---

### 3. Layout and Navigation

#### Task 3.1: Root Layout Component
- [ ] **Status**: Not Started
- **Description**: Create main layout with navigation sidebar and content area
- **Acceptance Criteria**:
  - [ ] Navigation sidebar with links to all pages
  - [ ] Active route highlighting
  - [ ] Responsive layout (sidebar collapsible on mobile)
  - [ ] Header with cluster status indicator
  - [ ] Footer with version info
- **Technical Approach**:
  - Create +layout.svelte in src/routes/
  - Use CSS Grid or Flexbox for layout structure
  - Add navigation component with SvelteKit's $page store for active route
  - Include connection status indicator (from WebSocket store)
  - Style with minimal CSS (no framework)
- **Files/Components**:
  - [ ] `dashboard/frontend/src/routes/+layout.svelte` - root layout
  - [ ] `dashboard/frontend/src/lib/components/Navigation.svelte` - nav component
  - [ ] `dashboard/frontend/src/lib/components/Header.svelte` - header component
- **Dependencies**: Task 2.2
- **Complexity**: M

#### Task 3.2: Global Styles
- [ ] **Status**: Not Started
- **Description**: Create global CSS styles and CSS custom properties for theming
- **Acceptance Criteria**:
  - [ ] CSS custom properties for colors, spacing, typography
  - [ ] Consistent spacing scale
  - [ ] Typography scale
  - [ ] Dark color scheme (primary use case)
  - [ ] Responsive breakpoints defined
- **Technical Approach**:
  - Create global.css with CSS custom properties
  - Define color palette suitable for dark mode
  - Set up typography using system fonts
  - Include CSS reset/normalize
  - Import in +layout.svelte
- **Files/Components**:
  - [ ] `dashboard/frontend/src/app.css` - global styles
  - [ ] `dashboard/frontend/static/fonts/` - web fonts if needed
- **Dependencies**: Task 3.1
- **Complexity**: S

---

### 4. Reusable Components

#### Task 4.1: GPUCard Component
- [ ] **Status**: Not Started
- **Description**: Display GPU status with utilization, memory, temperature, and model loaded
- **Acceptance Criteria**:
  - [ ] Shows GPU index and name
  - [ ] Memory usage bar (used/total)
  - [ ] Utilization percentage
  - [ ] Temperature with color coding
  - [ ] Currently loaded model (if any)
  - [ ] Visual indicator for GPU state (idle/active/error)
- **Technical Approach**:
  - Create Svelte component accepting GPUState as prop
  - Use progress bars for memory and utilization
  - Color-code temperature (green < 70C, yellow < 80C, red >= 80C)
  - Display model name or "Idle"
  - Add hover tooltip for full GPU details
- **Files/Components**:
  - [ ] `dashboard/frontend/src/lib/components/GPUCard.svelte` - GPU card component
- **Dependencies**: Task 2.3
- **Complexity**: M

#### Task 4.2: MachineCard Component
- [ ] **Status**: Not Started
- **Description**: Display machine overview with CPU, memory, and GPU count
- **Acceptance Criteria**:
  - [ ] Machine hostname and ID
  - [ ] Connection status (online/offline)
  - [ ] CPU load percentage
  - [ ] Memory usage (used/total GB)
  - [ ] GPU count (used/total)
  - [ ] Clickable to navigate to machine detail page
- **Technical Approach**:
  - Create Svelte component accepting MachineState as prop
  - Show connection indicator (dot: green=online, red=offline)
  - Display summary stats with icons
  - Add click handler to navigate to /machine/[id]
  - Style as card with hover effect
- **Files/Components**:
  - [ ] `dashboard/frontend/src/lib/components/MachineCard.svelte` - machine card component
- **Dependencies**: Task 2.3
- **Complexity**: M

#### Task 4.3: StatusBadge Component
- [ ] **Status**: Not Started
- **Description**: Reusable badge for displaying status (online/offline, running/stopped, etc.)
- **Acceptance Criteria**:
  - [ ] Accepts status string and variant prop
  - [ ] Color-coded by status type
  - [ ] Small and large sizes
  - [ ] Optional icon
- **Technical Approach**:
  - Create small Svelte component with props: status, variant, size
  - Use CSS classes for color variants (success, error, warning, info)
  - Include optional icon slot
  - Keep styling minimal and consistent
- **Files/Components**:
  - [ ] `dashboard/frontend/src/lib/components/StatusBadge.svelte` - badge component
- **Dependencies**: Task 1.1
- **Complexity**: S

#### Task 4.4: ModelLoadingIndicator Component
- [ ] **Status**: Not Started
- **Description**: Spinner/progress indicator for model loading state
- **Acceptance Criteria**:
  - [ ] Animated loading spinner
  - [ ] Optional text message
  - [ ] Estimated time remaining (if available)
  - [ ] Can be used inline or full-screen
- **Technical Approach**:
  - Create Svelte component with CSS animation
  - Accept props: message, size, fullscreen
  - Use CSS keyframe animation for spinner
  - Display optional loading text
- **Files/Components**:
  - [ ] `dashboard/frontend/src/lib/components/LoadingIndicator.svelte` - loading indicator
- **Dependencies**: Task 1.1
- **Complexity**: S

#### Task 4.5: LogViewer Component
- [ ] **Status**: Not Started
- **Description**: Display log entries with filtering and auto-scroll
- **Acceptance Criteria**:
  - [ ] Display log entries with timestamp, level, message
  - [ ] Color-coded by log level (info, warning, error)
  - [ ] Auto-scroll to bottom for new entries
  - [ ] Option to pause auto-scroll
  - [ ] Filter by log level
- **Technical Approach**:
  - Create Svelte component accepting log entries array
  - Use virtual scrolling for performance (or limit visible entries)
  - Add filter controls for level
  - Implement auto-scroll with pause button
  - Style with monospace font
- **Files/Components**:
  - [ ] `dashboard/frontend/src/lib/components/LogViewer.svelte` - log viewer component
- **Dependencies**: Task 2.3
- **Complexity**: M

---

### 5. Page Components

#### Task 5.1: Cluster Overview Page
- [ ] **Status**: Not Started
- **Description**: Main dashboard showing cluster-wide status (root route /)
- **Acceptance Criteria**:
  - [ ] Summary stats: total GPUs, used GPUs, free GPUs, machines online
  - [ ] List of all machines with MachineCard components
  - [ ] List of currently running models
  - [ ] Real-time updates from WebSocket
  - [ ] Link to each machine detail page
- **Technical Approach**:
  - Create +page.svelte in src/routes/
  - Subscribe to cluster state store
  - Display summary statistics at top
  - Render grid of MachineCard components
  - Show table of running models with machine assignments
  - Add page load function to fetch initial state via API
- **Files/Components**:
  - [ ] `dashboard/frontend/src/routes/+page.svelte` - cluster overview page
  - [ ] `dashboard/frontend/src/routes/+page.ts` - page load function
- **Dependencies**: Task 2.1, Task 2.2, Task 4.2
- **Complexity**: L

#### Task 5.2: Machine Detail Page
- [ ] **Status**: Not Started
- **Description**: Detailed view of single machine (route: /machine/[id])
- **Acceptance Criteria**:
  - [ ] Machine hostname, ID, connection status
  - [ ] CPU details (model, cores, load percentage)
  - [ ] Memory usage (total, used, available)
  - [ ] Network interfaces with IP addresses and speeds
  - [ ] All GPUs displayed with GPUCard components
  - [ ] Running containers list
  - [ ] Real-time updates
  - [ ] Back button to cluster overview
- **Technical Approach**:
  - Create +page.svelte in src/routes/machine/[id]/
  - Use dynamic route parameter for machine ID
  - Load machine details via API client
  - Subscribe to cluster state for real-time updates
  - Display detailed stats in organized sections
  - Render GPUCard for each GPU
- **Files/Components**:
  - [ ] `dashboard/frontend/src/routes/machine/[id]/+page.svelte` - machine detail page
  - [ ] `dashboard/frontend/src/routes/machine/[id]/+page.ts` - load function
- **Dependencies**: Task 2.1, Task 2.2, Task 4.1
- **Complexity**: L

#### Task 5.3: Chat/Test Interface Page
- [ ] **Status**: Not Started
- **Description**: Interactive chat interface for testing models (route: /chat)
- **Acceptance Criteria**:
  - [ ] Model selector dropdown
  - [ ] Text input for messages
  - [ ] Send button (disabled while loading)
  - [ ] Chat history display
  - [ ] Streaming response display (word-by-word)
  - [ ] Loading indicator during model loading
  - [ ] Error handling for failed requests
  - [ ] Clear chat button
- **Technical Approach**:
  - Create +page.svelte in src/routes/chat/
  - Implement SSE (Server-Sent Events) client for streaming
  - Fetch available models from /v1/models endpoint
  - Send requests to /v1/chat/completions
  - Parse SSE stream and update UI incrementally
  - Store chat history in component state
  - Handle keepalive messages during model loading
- **Files/Components**:
  - [ ] `dashboard/frontend/src/routes/chat/+page.svelte` - chat page
  - [ ] `dashboard/frontend/src/lib/api/streaming.ts` - SSE client
  - [ ] `dashboard/frontend/src/lib/components/ChatMessage.svelte` - message component
- **Dependencies**: Task 2.1, Task 4.4
- **Complexity**: XL

#### Task 5.4: Logs Page
- [ ] **Status**: Not Started
- **Description**: View system logs with filtering (route: /logs)
- **Acceptance Criteria**:
  - [ ] Fetch logs from /api/logs endpoint
  - [ ] Display using LogViewer component
  - [ ] Filter by log level (info, warning, error)
  - [ ] Filter by machine (optional)
  - [ ] Search by keyword
  - [ ] Pagination or infinite scroll
  - [ ] Refresh button
- **Technical Approach**:
  - Create +page.svelte in src/routes/logs/
  - Load logs via API client with query parameters
  - Use LogViewer component for display
  - Add filter controls for level and machine
  - Implement search with debounced input
  - Add pagination or load-more button
- **Files/Components**:
  - [ ] `dashboard/frontend/src/routes/logs/+page.svelte` - logs page
  - [ ] `dashboard/frontend/src/routes/logs/+page.ts` - load function
- **Dependencies**: Task 2.1, Task 4.5
- **Complexity**: M

---

### 6. Streaming and Real-Time Features

#### Task 6.1: Server-Sent Events (SSE) Client
- [ ] **Status**: Not Started
- **Description**: Implement SSE client for streaming responses from chat endpoint
- **Acceptance Criteria**:
  - [ ] Connect to SSE endpoint
  - [ ] Parse data: events
  - [ ] Handle keepalive messages
  - [ ] Yield tokens as they arrive
  - [ ] Detect [DONE] signal
  - [ ] Error handling for connection failures
- **Technical Approach**:
  - Use EventSource API for SSE
  - Create async generator function that yields chunks
  - Parse JSON from data: lines
  - Distinguish keepalive from actual tokens
  - Close connection on [DONE] or error
  - Provide cancellation mechanism
- **Files/Components**:
  - [ ] `dashboard/frontend/src/lib/api/streaming.ts` - SSE client implementation
- **Dependencies**: Task 2.1
- **Complexity**: L

#### Task 6.2: Real-Time Cluster State Updates
- [ ] **Status**: Not Started
- **Description**: Wire WebSocket updates to all pages for live data
- **Acceptance Criteria**:
  - [ ] Cluster overview updates when machines change
  - [ ] Machine detail page updates when that machine's stats change
  - [ ] Connection status indicator updates in header
  - [ ] No page refresh required for updates
  - [ ] Smooth transitions (no jarring changes)
- **Technical Approach**:
  - Ensure cluster state store is subscribed in all relevant pages
  - Use reactive statements ($:) to trigger UI updates
  - Add CSS transitions for smooth visual changes
  - Test with multiple machines connecting/disconnecting
- **Files/Components**:
  - [ ] Updates to all page components to subscribe to store
- **Dependencies**: Task 2.2, Task 5.1, Task 5.2
- **Complexity**: M

---

### 7. Error Handling and Edge Cases

#### Task 7.1: Error Boundary Component
- [ ] **Status**: Not Started
- **Description**: Create error boundary for graceful error handling
- **Acceptance Criteria**:
  - [ ] Catch and display errors without crashing app
  - [ ] Show user-friendly error messages
  - [ ] Provide retry mechanism
  - [ ] Log errors to console for debugging
- **Technical Approach**:
  - Create Svelte component with error slot
  - Wrap page content in error boundary
  - Display error state with message and retry button
  - Reset error state on retry
- **Files/Components**:
  - [ ] `dashboard/frontend/src/lib/components/ErrorBoundary.svelte` - error boundary
- **Dependencies**: Task 1.1
- **Complexity**: S

#### Task 7.2: Empty States
- [ ] **Status**: Not Started
- **Description**: Create components for empty states (no machines, no logs, etc.)
- **Acceptance Criteria**:
  - [ ] Empty state for cluster overview (no machines connected)
  - [ ] Empty state for logs page (no logs)
  - [ ] Empty state for chat history (no messages)
  - [ ] Helpful messaging and next steps
- **Technical Approach**:
  - Create EmptyState component with icon, message, and optional action
  - Use in each page when data is empty
  - Provide guidance on what to do next
- **Files/Components**:
  - [ ] `dashboard/frontend/src/lib/components/EmptyState.svelte` - empty state component
- **Dependencies**: Task 1.1
- **Complexity**: S

#### Task 7.3: Loading States
- [ ] **Status**: Not Started
- **Description**: Add loading skeletons/spinners for all async operations
- **Acceptance Criteria**:
  - [ ] Skeleton loaders for page initial load
  - [ ] Loading indicators for API calls
  - [ ] Disabled states for buttons during actions
  - [ ] Consistent loading UX across all pages
- **Technical Approach**:
  - Create skeleton components for cards and lists
  - Show skeletons while data is loading
  - Disable buttons and show spinner during actions
  - Use Svelte's #await blocks where appropriate
- **Files/Components**:
  - [ ] `dashboard/frontend/src/lib/components/Skeleton.svelte` - skeleton loader
  - [ ] Updates to all pages to show loading states
- **Dependencies**: Task 4.4
- **Complexity**: M

#### Task 7.4: API Error Handling
- [ ] **Status**: Not Started
- **Description**: Implement consistent error handling for all API calls
- **Acceptance Criteria**:
  - [ ] Display error messages from API
  - [ ] Retry mechanism for transient failures
  - [ ] Timeout handling
  - [ ] Network error detection
  - [ ] User-friendly error messages
- **Technical Approach**:
  - Enhance API client with error parsing
  - Create error notification component (toast/banner)
  - Show specific error messages from backend
  - Add retry logic for 5xx errors
  - Handle offline state gracefully
- **Files/Components**:
  - [ ] `dashboard/frontend/src/lib/components/ErrorNotification.svelte` - error notification
  - [ ] `dashboard/frontend/src/lib/api/client.ts` - enhanced error handling
- **Dependencies**: Task 2.1
- **Complexity**: M

---

### 8. Build and Integration

#### Task 8.1: Production Build Configuration
- [ ] **Status**: Not Started
- **Description**: Optimize build configuration for production deployment
- **Acceptance Criteria**:
  - [ ] Minified JavaScript and CSS
  - [ ] Code splitting for optimal loading
  - [ ] Source maps disabled in production
  - [ ] Build size under 500KB (uncompressed)
  - [ ] No console.log statements in production build
- **Technical Approach**:
  - Configure Vite for production mode
  - Enable minification and tree-shaking
  - Set up code splitting for routes
  - Remove console.log via Vite plugin
  - Verify build output size
- **Files/Components**:
  - [ ] `dashboard/frontend/vite.config.js` - production optimizations
  - [ ] `dashboard/frontend/svelte.config.js` - adapter settings
- **Dependencies**: Task 1.2
- **Complexity**: M

#### Task 8.2: FastAPI Static File Serving
- [ ] **Status**: Not Started
- **Description**: Configure FastAPI to serve static frontend build
- **Acceptance Criteria**:
  - [ ] FastAPI serves static files from build/ directory
  - [ ] SPA fallback to index.html for client-side routing
  - [ ] Correct MIME types for all assets
  - [ ] Frontend accessible at http://localhost:8080/
  - [ ] API routes not conflicting with frontend routes
- **Technical Approach**:
  - Mount StaticFiles in FastAPI for /assets and other static paths
  - Add catch-all route for SPA fallback (returns index.html)
  - Ensure API routes (/api/, /v1/, /ws/) are prioritized
  - Test all routes work correctly
- **Files/Components**:
  - [ ] `dashboard/backend/main.py` - static file mounting
- **Dependencies**: Task 8.1
- **Complexity**: M

#### Task 8.3: Development Workflow
- [ ] **Status**: Not Started
- **Description**: Set up development workflow with hot reload for both frontend and backend
- **Acceptance Criteria**:
  - [ ] Frontend dev server runs on port 5173
  - [ ] Backend runs on port 8080
  - [ ] Frontend proxies API requests to backend
  - [ ] Hot reload works for both frontend and backend
  - [ ] Single command to start both servers
- **Technical Approach**:
  - Configure Vite proxy to forward /api/, /v1/, /ws/ to localhost:8080
  - Create dev script that starts both servers (using concurrently or similar)
  - Test hot reload for Svelte components and Python files
  - Document development workflow
- **Files/Components**:
  - [ ] `dashboard/frontend/vite.config.js` - proxy configuration
  - [ ] `dashboard/dev/start-dev.sh` - development startup script
- **Dependencies**: Task 1.2
- **Complexity**: M

---

### 9. Testing and Validation

#### Task 9.1: Component Testing (Optional)
- [ ] **Status**: Not Started
- **Description**: Set up basic component testing with Vitest
- **Acceptance Criteria**:
  - [ ] Vitest configured for Svelte components
  - [ ] Tests for utility functions
  - [ ] Tests for API client
  - [ ] Tests can be run with npm test
- **Technical Approach**:
  - Install @testing-library/svelte and vitest
  - Write tests for utility functions (format, gpu helpers)
  - Write tests for API client (with mocked fetch)
  - Add test script to package.json
- **Files/Components**:
  - [ ] `dashboard/frontend/vitest.config.js` - Vitest configuration
  - [ ] `dashboard/frontend/src/lib/utils/__tests__/` - utility tests
  - [ ] `dashboard/frontend/src/lib/api/__tests__/` - API client tests
- **Dependencies**: Task 2.1, Task 2.3
- **Complexity**: M

#### Task 9.2: Manual Testing Checklist
- [ ] **Status**: Not Started
- **Description**: Create manual testing checklist for all features
- **Acceptance Criteria**:
  - [ ] Test plan document created
  - [ ] All pages tested with real backend
  - [ ] WebSocket reconnection tested
  - [ ] Streaming chat tested
  - [ ] Error states tested
  - [ ] Mobile responsiveness tested
- **Technical Approach**:
  - Create markdown document with test scenarios
  - Test each page with backend running
  - Simulate machine connection/disconnection
  - Test chat with various models
  - Test error conditions (network failure, API errors)
  - Test on different screen sizes
- **Files/Components**:
  - [ ] `dashboard/frontend/TESTING.md` - manual testing checklist
- **Dependencies**: All previous tasks
- **Complexity**: L

#### Task 9.3: Cross-Browser Testing
- [ ] **Status**: Not Started
- **Description**: Verify frontend works in major browsers
- **Acceptance Criteria**:
  - [ ] Works in Chrome/Edge (Chromium)
  - [ ] Works in Firefox
  - [ ] Works in Safari (if available)
  - [ ] WebSocket works in all browsers
  - [ ] SSE works in all browsers
- **Technical Approach**:
  - Test in Chrome (primary)
  - Test in Firefox
  - Test in Safari if available
  - Verify WebSocket and EventSource APIs work
  - Fix any browser-specific issues
- **Files/Components**:
  - No specific files (testing task)
- **Dependencies**: Task 9.2
- **Complexity**: S

---

### 10. Documentation

#### Task 10.1: Frontend README
- [ ] **Status**: Not Started
- **Description**: Create README for frontend development
- **Acceptance Criteria**:
  - [ ] Setup instructions
  - [ ] Development workflow documented
  - [ ] Build process explained
  - [ ] Project structure overview
  - [ ] Common troubleshooting tips
- **Technical Approach**:
  - Create README.md in dashboard/frontend/
  - Document npm scripts
  - Explain directory structure
  - Provide examples for adding new pages/components
  - Include common issues and solutions
- **Files/Components**:
  - [ ] `dashboard/frontend/README.md` - frontend documentation
- **Dependencies**: All previous tasks
- **Complexity**: S

#### Task 10.2: Component Documentation
- [ ] **Status**: Not Started
- **Description**: Add JSDoc comments to all components and utilities
- **Acceptance Criteria**:
  - [ ] All components have prop descriptions
  - [ ] All utilities have parameter descriptions
  - [ ] Usage examples in comments
  - [ ] Type information in JSDoc
- **Technical Approach**:
  - Add JSDoc comments to component props
  - Document utility function parameters and return values
  - Include usage examples in comments
  - Ensure TypeScript types are accurate
- **Files/Components**:
  - Updates to all component and utility files
- **Dependencies**: All previous tasks
- **Complexity**: M

---

## Task Summary

| Section | Task Count | Total Complexity |
|---------|------------|------------------|
| 1. Project Initialization | 3 | S + S + S = 3 Small |
| 2. Core Infrastructure | 3 | M + L + S = 1 Large, 1 Medium, 1 Small |
| 3. Layout and Navigation | 2 | M + S = 1 Medium, 1 Small |
| 4. Reusable Components | 5 | M + M + S + S + M = 3 Medium, 2 Small |
| 5. Page Components | 4 | L + L + XL + M = 1 XL, 2 Large, 1 Medium |
| 6. Streaming and Real-Time | 2 | L + M = 1 Large, 1 Medium |
| 7. Error Handling | 4 | S + S + M + M = 2 Medium, 2 Small |
| 8. Build and Integration | 3 | M + M + M = 3 Medium |
| 9. Testing and Validation | 3 | M + L + S = 1 Large, 1 Medium, 1 Small |
| 10. Documentation | 2 | S + M = 1 Medium, 1 Small |
| **Total** | **31 tasks** | **1 XL, 5 L, 13 M, 12 S** |

---

## Dependencies Graph

```
1.1 (SvelteKit Setup)
├── 1.2 (Build Integration)
├── 1.3 (Dependencies)
├── 2.1 (API Client)
├── 2.3 (Utils)
└── 3.1 (Layout)

2.1 (API Client)
├── 5.1 (Cluster Overview)
├── 5.2 (Machine Detail)
├── 5.3 (Chat)
├── 5.4 (Logs)
└── 6.1 (SSE Client)

2.2 (WebSocket Store)
├── 3.1 (Layout)
├── 5.1 (Cluster Overview)
├── 5.2 (Machine Detail)
└── 6.2 (Real-Time Updates)

4.x (Reusable Components)
├── 5.1 (Cluster Overview)
├── 5.2 (Machine Detail)
└── 5.3 (Chat)

5.x (Pages)
└── 9.2 (Manual Testing)

8.1 (Build Config)
└── 8.2 (FastAPI Integration)

9.x (Testing)
└── 10.x (Documentation)
```

---

## Recommended Implementation Order

### Week 1: Foundation
1. Task 1.1, 1.2, 1.3 - Project setup
2. Task 2.1 - API client
3. Task 2.3 - Utilities
4. Task 3.1, 3.2 - Layout and styles

### Week 2: Components and First Page
5. Task 4.1, 4.2, 4.3, 4.4 - Reusable components
6. Task 2.2 - WebSocket store
7. Task 5.1 - Cluster Overview page
8. Task 7.1, 7.2, 7.3 - Error and loading states

### Week 3: Detail Pages
9. Task 5.2 - Machine Detail page
10. Task 4.5 - LogViewer component
11. Task 5.4 - Logs page
12. Task 6.2 - Real-time updates

### Week 4: Chat and Integration
13. Task 6.1 - SSE client
14. Task 5.3 - Chat interface
15. Task 8.1, 8.2, 8.3 - Build and FastAPI integration
16. Task 7.4 - API error handling

### Week 5: Testing and Polish
17. Task 9.1, 9.2, 9.3 - Testing
18. Task 10.1, 10.2 - Documentation
19. Final polish and bug fixes

---

## Exit Criteria Verification

- [ ] All 4 pages (Cluster Overview, Machine Detail, Chat, Logs) are functional
- [ ] Real-time updates via WebSocket working on all pages
- [ ] Static build successfully served by FastAPI at http://localhost:8080/
- [ ] Chat interface can send requests to models
- [ ] Streaming responses display incrementally in chat
- [ ] Loading indicators shown during model loading
- [ ] Error handling graceful for all API failures
- [ ] No console errors in production build
- [ ] Build size under 500KB (uncompressed)
- [ ] Manual testing checklist completed

---

## Notes

- Keep the UI lightweight and fast - no heavy UI frameworks
- Prioritize functionality over aesthetics (this is a personal cluster tool)
- Dark mode as default (easier on eyes for monitoring)
- Ensure all network calls have proper error handling
- WebSocket reconnection is critical for reliability
- SSE streaming must handle keepalive during model loading
- Test with real backend as early as possible
