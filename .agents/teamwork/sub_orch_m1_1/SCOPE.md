# Scope: Milestone 1 (Knowledge Graph & Mereology)

## Architecture
Relational SQLite/PostgreSQL knowledge graph engine with recursive CTE upward traversal linking clinical conditions to BodyParts3D 3D meshes.

## Feature Inventory
| # | Feature ID | Feature Name | Status |
|---|---|---|---|
| 1 | R3.1 | Unified Spatial-Clinical Schema | IN_PROGRESS |
| 2 | R3.2 | Recursive Mereological Traversal Engine | IN_PROGRESS |
| 3 | R3.3 | >80% Grounding Coverage Elevation | IN_PROGRESS |
| 4 | R3.4 | Tripartite Concept Crosswalk | IN_PROGRESS |

## Interface Contracts
- `rag/mereology.py` exports:
  - `resolve_structure(fma_or_name: str) -> Optional[ResolvedStructure]`
  - `climb_to_visible_mesh(fma_id: str, max_depth: int = 5) -> Tuple[str, int]`
  - `resolve_condition(condition_label_or_id: str) -> List[ResolvedStructure]`
  - `get_mereology_tree(fma_id: str) -> Dict[str, List[Dict[str, str]]]`
  - `compute_grounding_metrics() -> Dict[str, float]`
- Storage:
  - `data/graph/mereology_graph.sqlite3` with tables: `spatial_concepts`, `spatial_relations`, `clinical_concepts`, `spatial_clinical_crosswalk`.
