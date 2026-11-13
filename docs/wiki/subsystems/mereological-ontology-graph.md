# Subsystem: Mereological Ontology Graph

## Problem
On 2026-11-13, as of `dr-ishaanwadhwa/medevolv-mentor@2ab61ea`, the static crosswalk (`data/graph/atlas_crosswalk.jsonl`) achieved only 31.7% coverage on certified anatomical structures (114/360) and 2.3% on clinical conditions (115/4,978) due to strict 1-to-1 string matching.

## Solution
On 2026-11-13, the team approved implementing a recursive mereological graph traversal engine:
- Ingests FMA mereology relationships (`PART_OF`, `BRANCH_OF`, `SUPPLIED_BY`, `DRAINED_BY`, `INNERVATED_BY`).
- When a clinical entity or sub-structure lacks an independent 3D mesh, the traversal walks up the mereological tree to the nearest ancestor with geometry in the BodyParts3D catalogue.
- Traversal targets raising condition spatial grounding to >80%.

## Related Pages
- [ADR-001: Unified AI-Native Architecture](../decisions/ADR-001-unified-ai-native-architecture.md)
- [Spatial-Semantic Bridge](spatial-semantic-bridge.md)
