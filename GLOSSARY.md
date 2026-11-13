# Medical Graph & Ontology Densification

The semantic network, taxonomy, and relation-mining layer bridging medical textbook knowledge with retrieval-augmented generation.

## Language

**Certified Fact**:
A clinical triple (subject, predicate, object) verified against a verbatim textbook passage quote and approved by the verifier gate.
_Avoid_: Unverified assertion, heuristic link, hallucination

**Heading Concept**:
A navigational concept derived from a Table of Contents (ToC) or section heading, representing a topic discussed in a text.
_Avoid_: Clinical entity, extracted fact

**Generic Facet**:
A structural or functional aspect of a section (such as "Overview", "Nerves", "Uses", "Adverse effects") that qualifies its parent concept rather than forming an independent entity.
_Avoid_: Entity node, standalone topic

**Composite Heading**:
A qualified anatomical structure name formed by combining a positional sub-part with its parent region (e.g., "Roof of the inguinal canal").
_Avoid_: Bare positional token, floating part

**Heading Alias**:
An acronym or synonym extracted directly from parenthetical text within a chapter or section heading.
_Avoid_: Inferred alias, heuristic synonym

**Graph Block**:
The structured context segment injected into the RAG prompt containing exclusively certified facts for grounded clinical reasoning.
_Avoid_: Retrieval chunk, mention context

**Hub Node**:
A structural aggregator node (such as an organ system, drug class, or condition category) that organizes and bridges related concepts across components.
_Avoid_: Super-node, hairball, generic disease
