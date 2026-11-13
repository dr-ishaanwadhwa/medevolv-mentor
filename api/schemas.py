"""Wire contracts for the API. Citations are pointers (+ one short excerpt), never passage text.

Server-Sent Events from POST /api/chat/stream, in order: step (0..n), answer, spatial, done  |  error (ends the stream).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

EXCERPT_MAX = 300      # same cap app.py shows; the trailing ellipsis may add one character
EXCERPT_FIELD_MAX = EXCERPT_MAX + 1


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class StepEvent(BaseModel):
    stage: str
    title: str
    detail: str = ""
    status: Literal["ok", "warn", "stop"] = "ok"
    ms: float = 0.0


class Citation(BaseModel):
    """Pointer to a textbook location. `excerpt` is the optional short snippet the Streamlit app also shows."""
    book: str
    edition: str = ""
    chapter: str = ""
    pages: str = ""
    section_id: str = ""
    excerpt: str | None = Field(default=None, max_length=EXCERPT_FIELD_MAX)


class AnswerCitation(Citation):
    index: int                      # the [n] used in the answer text
    cited: bool                     # False = retrieved but not cited in the text


class AnswerEvent(BaseModel):
    text: str
    status: str
    route: str
    citations: list[AnswerCitation] = []


class SpatialAction(BaseModel):
    """A navigation hint for the 3D viewer. Never a clinical claim."""
    action: Literal["highlight"] = "highlight"
    fma_ids: list[str]
    label: str
    tier: Literal["navigation"] = "navigation"


class SpatialEvent(BaseModel):
    actions: list[SpatialAction] = []


class DoneEvent(BaseModel):
    ms: float


class ErrorEvent(BaseModel):
    message: str
    error_type: str = ""


class AtlasLink(BaseModel):
    label: str
    atlas_name: str
    fma_ids: list[str]
    url: str | None = None


class ConceptRef(BaseModel):
    id: str
    label: str
    type: str
    aliases: list[str] = []
    degree: int = 0
    books: list[str] = []


class RelatedConcept(BaseModel):
    id: str
    label: str
    type: str
    shared_facts: int = 0
    tier: str = "derived"


class SpatialResolveResponse(BaseModel):
    query: dict[str, str]
    fma_ids: list[str]
    label: str
    atlas: list[AtlasLink]
    concept: ConceptRef | None = None
    citations: list[Citation]
    related: list[RelatedConcept]
    tier: Literal["navigation"] = "navigation"


class ConceptHit(BaseModel):
    id: str
    label: str
    type: str
    degree: int = 0


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    llm_backend: str
    atlas_enabled: bool
    ontology_loaded: bool
