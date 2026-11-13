# Structural Heading Densification and Safety Boundary

To increase graph connectivity without diluting clinical grounding, Table of Contents and section headings are densified into a dedicated navigation layer (`data/graph/headings.jsonl`) rather than mixed into certified facts (`clinical_ontology.jsonl`). Non-T1 records are strictly barred from entering the RAG answer `graph_block`, generic facets are attached as parent metadata instead of standalone entities, and transitive propagation of clinical relations across hierarchy or class-membership edges is forbidden.
