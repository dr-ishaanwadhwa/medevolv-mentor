# Standards: Engineering Principles

## Principles
On 2026-11-13, the Chief of Staff established the following engineering rules for all subagents and pull requests:

1. **No Workarounds Rule:**
   - No `window.postMessage` shims between iframes.
   - No arbitrary client-side `setTimeout` delays to wait for WebGL assets.
   - State synchronization must flow through the typed Zustand store and validated SSE contracts.

2. **Pointer-Only Textbook Citations:**
   - As established in `docs/research/v2 research.md`, Indian legal precedent under Section 52(1)(i) restricts educational exemptions to institutions, excluding commercial B2C applications.
   - The platform strictly outputs original synthetic prose, certified structured facts, and `(Book, Edition, Chapter, Page)` verification pointers, never verbatim copyrighted textbook paragraphs.

3. **High-Level Seam Testing:**
   - Tests must evaluate external observable behavior (FastAPI HTTP/SSE endpoints and React UI interactions), not private module internals.

## Related Pages
- [ADR-001: Unified AI-Native Architecture](../decisions/ADR-001-unified-ai-native-architecture.md)
