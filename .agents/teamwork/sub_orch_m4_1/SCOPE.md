# Scope: Milestone 4 (Frontend Workspace & 3D WebGL)

## Architecture
Next.js 15 / React 19 PWA monorepo workspace in `apps/web` with direct Three.js WebGL canvas embedding and Zustand state management.

## Feature Inventory
| # | Feature ID | Feature Name | Status |
|---|---|---|---|
| 1 | R2.1 | Next.js 15 / React 19 Unified PWA | IN_PROGRESS |
| 2 | R2.2 | Native Three.js WebGL Canvas (15 Draw Calls) | IN_PROGRESS |
| 3 | R2.3 | Zustand Global State Store (`useSpatialStore`) | IN_PROGRESS |
| 4 | R2.4 | Raycast Mesh Click Callback | IN_PROGRESS |
| 5 | R2.5 | Dual-Pane / Responsive Bottom Drawer | IN_PROGRESS |
| 6 | R2.6 | IndexedDB Offline PWA Cache | IN_PROGRESS |

## Interface Contracts
- Consume SSE stream from `POST /api/chat/stream`:
  - Handle `SpatialAction` events: `highlight`, `set_camera`, `dissect`, `reset`.
- Dispatch HTTP POST to `/api/spatial/resolve`:
  - Payload: `{ identifier: fmaId, includeHierarchy: true, includeCitations: true }`
  - Populate Clinical Drawer with returned pointers, conditions, and mereology.
