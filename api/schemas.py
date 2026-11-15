"""Wire contracts for the API. Citations are pointers (+ one short excerpt), never passage text.

Server-Sent Events from POST /api/chat/stream, in order: step (0..n), answer, spatial, done  |  error (ends the stream).
POST /api/why/stream: step (0..n), verdict, done  |  error. See api/README.md.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

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


# ---------------------------------------------------------------- v2 additions (W1): why / concept page / answers / feedback

class WhyRequest(BaseModel):
    question: str = Field(min_length=1, max_length=3000)
    options: list[str] = Field(min_length=2, max_length=6)
    chosen: int = Field(ge=0)


class VerdictEvent(BaseModel):
    """SSE `verdict` from POST /api/why/stream. `status="insufficient"`: the books do not settle it (correct_option is null)."""
    status: Literal["verdict", "insufficient"]
    correct_option: int | None = None
    chosen_wrong_because: str = ""
    explanation: str = ""                       # markdown, [n] markers index into `citations`
    citations: list[AnswerCitation] = []
    viva_questions: list[str] = []              # exactly 3 when status == "verdict"


class ConceptLink(BaseModel):
    id: str
    label: str
    type: str
    predicate: str | None = None
    tier: str                                   # certified | derived | suggested | navigation


class ConceptSection(BaseModel):
    section_id: str
    book_id: str
    title: str = ""
    path: str = ""
    primary: bool = False                       # the book's own section for this concept (heading names it)
    tier: str = "navigation"


class ConceptHub(BaseModel):
    hub_id: str
    label: str
    type: str
    tier: str


class SeeAlso(BaseModel):
    id: str | None = None                       # null when the co-mentioned phrase is not an ontology concept
    label: str
    score: float
    books: list[str] = []
    section_id: str = ""
    tier: Literal["suggested"] = "suggested"


class BodhiRef(BaseModel):
    bodhi_id: str
    name: str
    type: str = ""
    relation: str
    tier: str


class ConceptAtlas(BaseModel):
    link: str | None = None                     # None: unlinked, or ATLAS_URL unset
    structures: list[dict] = []                 # [{label, atlas_name, url}] a condition involves; [] when none


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    center: bool = False


class GraphEdge(BaseModel):
    source: str
    target: str
    predicate: str
    tier: str


class ConceptGraph(BaseModel):
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []


class ConceptPage(BaseModel):
    id: str
    label: str
    type: str
    aliases: list[str] = []
    books: list[str] = []
    degree: int = 0
    sections: list[ConceptSection] = []
    links_out: list[ConceptLink] = []
    links_in: list[ConceptLink] = []
    links_out_total: int = 0
    links_in_total: int = 0
    hubs: list[ConceptHub] = []
    see_also: list[SeeAlso] = []
    bodhi: list[BodhiRef] = []
    atlas: ConceptAtlas = ConceptAtlas()
    graph: ConceptGraph = ConceptGraph()


class NotFound(BaseModel):
    detail: str


class AnswerSave(BaseModel):
    kind: Literal["chat", "why"]
    question: str = Field(max_length=3000)
    payload: dict


class AnswerSaved(BaseModel):
    id: str


class AnswerRecord(BaseModel):
    id: str
    kind: Literal["chat", "why"]
    question: str
    payload: dict
    created_at: float


class FeedbackRequest(BaseModel):
    answer_id: str | None = Field(default=None, max_length=32)
    question: str | None = Field(default=None, max_length=3000)
    kind: Literal["wrong_citation", "unhelpful", "other"]
    note: str | None = Field(default=None, max_length=1000)


class FeedbackOk(BaseModel):
    ok: Literal[True] = True


class StoryExploreRequest(BaseModel):
    """'Try your own question' on the /how story. Whitespace-only questions are rejected (422)."""
    question: str = Field(min_length=1, max_length=300)

    @field_validator("question")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("question must not be blank")
        return v


class StoryNeighbour(BaseModel):
    i: int                  # index of the passage in the story map (scripts/build_library_map.py order)
    sim: float
    book: str               # textbook display name


class StoryExploreResponse(BaseModel):
    question: str
    refused: bool
    neighbours: list[StoryNeighbour] = []      # 12 nearest passages; [] when refused
    best: float | None
    min_similarity: float
    passes_floor: bool
    narration: str
