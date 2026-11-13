"""MedEvolv Mentor: Streamlit UI.  Run:  .venv/bin/streamlit run app.py

Three tabs:
  Ask                 chat; every answer carries its sources and a step-by-step record of how it was made
  How it works        the pipeline explained for a first-time viewer (diagram, stages, safety rules, evaluation)
  Explore conditions  5-level drill-down over the certified clinical ontology, with a source on every fact
"""
import functools
import hmac
import html
import os
import re
from collections import Counter

import streamlit as st

from rag import atlas, clinical_graph, config, diagrams, trace
from rag import ontology_facts as onto
from rag.answer import answer, answer_multihop
from rag.graph_component import clinical_graph as clinical_graph_view
from rag.trace import STAGES


def _safe(fn, default=None):
    """Run an optional panel call; any failure (missing data, bad index) just hides the panel."""
    try:
        return fn()
    except Exception:
        return default


@functools.cache
def onto_sections() -> int:
    """Distinct textbook sections that contributed at least one certified fact."""
    return len({(src.get("book_id"), src.get("section_id")) for f in onto.facts() for src in onto.sources(f)})

st.set_page_config(page_title="MedEvolv Mentor", page_icon="🩺", layout="wide",
                   initial_sidebar_state="collapsed")

# ---------------------------------------------------------------- style
st.html("""
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root { --ink:#15232a; --muted:#5a6b72; --line:#d7e0e2; --accent:#0f6b74; --accent-soft:#e2f0f1;
        --good:#1d7a46; --good-soft:#e3f3ea; --warn:#9a6200; --warn-soft:#fbf0db; --bad:#b0323a; --bad-soft:#f8e3e4;
        --card:#ffffff; --mono:"IBM Plex Mono", ui-monospace, Menlo, monospace; }
@media (prefers-color-scheme: dark) {
  :root { --ink:#e6eef0; --muted:#9fb2b8; --line:#2b3d43; --accent:#4fb3bd; --accent-soft:#17343a;
          --good:#6fd39b; --good-soft:#173324; --warn:#e8b25a; --warn-soft:#3a2d12; --bad:#f08a90; --bad-soft:#3d1a1d;
          --card:#14232a; }
}
.stApp, .stApp p, .stApp li, .stApp button, .stApp input, .stApp textarea, .stApp label { font-family: "Instrument Sans", system-ui, sans-serif; }
/* never override Streamlit's icon font, or icon names render as text */
[data-testid="stIconMaterial"], [class*="material-symbols"], [class*="MaterialSymbols"] { font-family: "Material Symbols Rounded" !important; }
/* demo-question buttons: show the whole question */
.stButton button { height: auto; min-height: 2.6rem; padding: .45rem .8rem; text-align: left; justify-content: flex-start; }
.stButton button p, .stButton button div { white-space: normal !important; overflow: visible !important; text-overflow: clip !important; text-align: left; line-height: 1.35; }
.block-container { padding-top: 1.6rem; max-width: 1100px; }
.mm-pills { display:flex; flex-wrap:wrap; gap:.3rem; margin:.1rem 0 .5rem; }
.mm-pills .mm-pill { margin-right:0; }
h1, h2, h3 { letter-spacing: -0.01em; }

.mm-hero { display:grid; gap:.55rem; padding: .4rem 0 1.1rem; border-bottom:1px solid var(--line); margin-bottom: .4rem; }
.mm-eyebrow { font: 500 .74rem var(--mono); letter-spacing:.09em; text-transform:uppercase; color:var(--accent); }
.mm-title { font-size: 2.3rem; font-weight: 700; line-height:1.1; color:var(--ink); margin:0; }
.mm-sub { color:var(--muted); font-size:1.05rem; max-width: 70ch; margin:0; }
.mm-chips { display:flex; flex-wrap:wrap; gap:.4rem; margin-top:.25rem; }
.mm-chip { font: 500 .78rem var(--mono); background: var(--accent-soft); color: var(--accent);
           padding: .18rem .6rem; border-radius: 999px; }

.mm-label { font: 500 .72rem var(--mono); letter-spacing:.07em; text-transform:uppercase; color:var(--muted); }
.mm-pill { display:inline-block; font:500 .74rem var(--mono); padding:.15rem .6rem; border-radius:999px; margin:0 .35rem .2rem 0; white-space:nowrap; }
.mm-pill.good { background:var(--good-soft); color:var(--good); }
.mm-pill.warn { background:var(--warn-soft); color:var(--warn); }
.mm-pill.bad  { background:var(--bad-soft);  color:var(--bad); }
.mm-pill.info { background:var(--accent-soft); color:var(--accent); }

/* step-by-step process timeline */
.mm-tl { list-style:none; margin:.2rem 0 0; padding:0; display:grid; gap:0; }
.mm-step { display:grid; grid-template-columns: 2.1rem 1fr auto; gap:.2rem .75rem; position:relative; padding:.55rem 0; }
.mm-step:not(:last-child)::before { content:""; position:absolute; left:1.02rem; top:2.3rem; bottom:-.4rem; width:2px; background:var(--line); }
.mm-dot { width:2.1rem; height:2.1rem; border-radius:50%; display:grid; place-items:center; font-size:1rem;
          background:var(--accent-soft); border:2px solid var(--card); box-shadow:0 0 0 1px var(--line); z-index:1; }
.mm-step.warn .mm-dot { background:var(--warn-soft); }
.mm-step.stop .mm-dot { background:var(--bad-soft); }
.mm-step .mm-body { min-width:0; }
.mm-stage { font:500 .68rem var(--mono); letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
.mm-step.warn .mm-stage { color:var(--warn); } .mm-step.stop .mm-stage { color:var(--bad); }
.mm-title-s { font-weight:600; color:var(--ink); line-height:1.3; }
.mm-detail { color:var(--muted); font-size:.9rem; line-height:1.45; overflow-wrap:anywhere; }
.mm-ms { font: .74rem var(--mono); color:var(--muted); white-space:nowrap; padding-top:.15rem; font-variant-numeric: tabular-nums; }
.mm-hits { margin:.35rem 0 0; padding:0; list-style:none; display:grid; gap:.2rem; }
.mm-hits li { display:grid; grid-template-columns: 2.6rem 1fr; gap:.5rem; font-size:.82rem; color:var(--muted); align-items:start; line-height:1.35; }
.mm-hits b { color: var(--ink); font-weight:600; }
.mm-bar { display:block; height:.38rem; background:var(--line); border-radius:999px; overflow:hidden; margin:.15rem 0 .2rem; max-width:22rem; }
.mm-bar > span { display:block; height:100%; background:var(--accent); }
.mm-sim { font: .74rem var(--mono); color:var(--ink); }
.mm-q { font-family: var(--mono); font-size:.8rem; color:var(--ink); background:var(--accent-soft); padding:.05rem .35rem; border-radius:4px; }

/* sources */
.mm-src { border:1px solid var(--line); border-radius:10px; padding:.7rem .85rem; background:var(--card); display:grid; gap:.3rem; margin-bottom:.5rem; }
.mm-src.cited { border-color: var(--accent); border-left-width:4px; }
.mm-src-ex { overflow-wrap:anywhere; }
.mm-empty { border:1px dashed var(--line); border-radius:12px; padding:.9rem 1rem; color:var(--muted); font-size:.92rem; margin:.4rem 0 .8rem; }
.mm-differ { border:1px solid var(--line); border-left:4px solid var(--warn); border-radius:10px; padding:.65rem .85rem; margin-bottom:.6rem; background:var(--card); display:grid; gap:.3rem; }
.mm-side { font-size:.86rem; color:var(--muted); line-height:1.45; padding-left:.6rem; border-left:2px solid var(--line); }
.mm-side b { color:var(--ink); }
.mm-src-head { display:flex; flex-wrap:wrap; gap:.4rem; align-items:center; }
.mm-src-n { font: 600 .8rem var(--mono); color:var(--accent); }
.mm-src-where { font-size:.88rem; color:var(--ink); font-weight:500; }
.mm-src-ex { font-size:.84rem; color:var(--muted); line-height:1.45; }

/* how-it-works cards */
.mm-card { border:1px solid var(--line); border-radius:12px; background:var(--card); padding:1rem 1.05rem; height:100%; display:grid; gap:.35rem; align-content:start; }
.mm-card h4 { margin:0; font-size:1.02rem; }
.mm-card p { margin:0; color:var(--muted); font-size:.92rem; line-height:1.5; }
.mm-num { font: 600 .74rem var(--mono); color:var(--accent); }

@media (max-width: 640px) {
  .block-container { padding: 1rem .8rem 4rem; }
  .mm-title { font-size: 1.65rem; }
  .mm-sub { font-size: .95rem; }
  .mm-step { grid-template-columns: 1.8rem 1fr; }
  .mm-dot { width:1.8rem; height:1.8rem; font-size:.85rem; }
  .mm-step:not(:last-child)::before { left:.86rem; top:2.1rem; }
  .mm-ms { grid-column: 2; padding-top:0; }
  .mm-hits li { grid-template-columns: 2.3rem 1fr; }
  .mm-card { height:auto; }
  .stTabs [data-baseweb="tab-list"] { overflow-x:auto; }
}
</style>
""")

# ---------------------------------------------------------------- optional login gate (set APP_PASSWORD to enable)
if os.getenv("APP_PASSWORD") and not st.session_state.get("authed"):
    st.title("🩺 MedEvolv Mentor")
    pw = st.text_input("Password", type="password")
    if pw and hmac.compare_digest(pw.encode(), os.environ["APP_PASSWORD"].encode()):
        st.session_state.authed = True
        st.rerun()
    elif pw:
        st.error("Wrong password.")
    st.stop()

STATUS = {
    "answered": ("Grounded answer", "good"),
    "not_in_sources": ("Not in the textbooks: declined", "warn"),
    "insufficient": ("Evidence insufficient: declined", "warn"),
    "personal_refusal": ("Personal medical advice: declined", "bad"),
}
ROUTE = {"graph": "Clinical case · graph route", "case": "Long case · focused look-ups",
         "decompose": "Compound · split into parts",
         "single": "Single question · direct search"}
BOOKS = {"tripathi": "KD Tripathi · Pharmacology", "guyton": "Guyton & Hall · Physiology",
         "robbins": "Robbins · Pathology", "davidson": "Davidson · Medicine", "micro": "Microbiology",
         "harrison": "Harrison · Internal Medicine",
         "grays": "Gray's · Anatomy"}

EXAMPLES = [
    ("Clinical case", "A patient has high fever, headache and joint pain after a mosquito bite. Likely diagnosis and treatment?"),
    ("Factual", "What is the drug of choice for absence seizures and why?"),
    ("Comparison", "Compare the mechanism of action of penicillins and aminoglycosides"),
    ("Physiology", "How does the baroreceptor reflex respond to a sudden fall in blood pressure?"),
    ("Off-topic", "Who won the 2011 cricket world cup?"),
    ("Personal advice", "My mother has TB, how much rifampicin should she take?"),
]

# ---------------------------------------------------------------- sidebar: settings
with st.sidebar:
    st.markdown("### Settings")
    if config.EXPERIMENTAL:
        retriever = st.radio("Retriever (experimental)", ["vector", "router", "stair"], horizontal=True)
    else:
        retriever = "vector"
    multihop = st.toggle("Multi-hop reasoning", value=True, disabled=retriever != "vector",
                         help="On: clinical cases go through the knowledge graph and compound questions are split. "
                              "Off: plain single-search RAG, for a before/after comparison.")
    st.caption(f"Model: `{config.LLM_BACKEND}` · Embeddings: `{config.LOCAL_EMBED_MODEL.split('/')[-1]}` · "
               f"Top-k {config.TOP_K} · Threshold {config.MIN_SIMILARITY:.2f}")
    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ---------------------------------------------------------------- header
st.html("""
<div class="mm-hero">
  <div class="mm-eyebrow">MedEvolv · study companion for medical students</div>
  <h1 class="mm-title">MedEvolv Mentor</h1>
  <p class="mm-sub">Ask exam questions or clinical cases. Every answer is built only from seven standard textbooks
  and an open clinical knowledge graph, cites its sources, and shows exactly how it was made.</p>
  <div class="mm-chips">
    <span class="mm-chip">7 textbooks</span><span class="mm-chip">2,611 sections</span>
    <span class="mm-chip">36,725 passages</span><span class="mm-chip">6,560-node clinical graph</span>
    <span class="mm-chip">cites every claim</span><span class="mm-chip">declines when unsure</span>
  </div>
</div>
""")

tab_ask, tab_how, tab_explore = st.tabs(["💬  Ask", "🔍  How it works", "🧭  Explore conditions"])


# ---------------------------------------------------------------- rendering helpers
def esc(s) -> str:
    return html.escape(str(s))


def corr_badge(f) -> str:
    """'N books' pill when several textbooks state the same fact (empty string otherwise)."""
    try:
        n = onto.corroboration(f)
    except Exception:
        return ""
    if n < 2:
        return ""
    names = ", ".join(BOOKS.get(b, b) for b in onto.books(f))
    return f'<span class="mm-pill good" title="{esc(names)}">{n} books</span>'


def cite_text(f) -> str:
    try:
        return onto.cite_all(f)
    except Exception:
        return onto.cite(f)


def by_corroboration(fs):
    return sorted(fs, key=lambda f: -onto.corroboration(f))      # stable: ties keep their order


JUNK = re.compile(r"^(?:[A-Z]\s){2,}[A-Z0-9\s]*$")       # running-header debris such as "U N I T I V"


def tidy_path(where: str) -> str:
    """'18 Nervous Regulation… › U N I T I V (pp. 222-231)' -> '18 Nervous Regulation… (pp. 222-231)'"""
    pages = ""
    m = re.search(r"\s*\((pp?\.[^)]*)\)\s*$", where)
    if m:
        pages, where = f" · {m.group(1)}", where[:m.start()]
    parts = [p for p in where.split(" › ") if p.strip() and not JUNK.match(p.strip())]
    return " › ".join(parts) + pages


def step_html(s) -> str:
    stage_label = STAGES.get(s.stage, ("", s.stage))[1]
    extra = ""
    if s.stage == "retrieve" and s.data.get("hits"):
        rows = "".join(
            f'<li><span class="mm-sim">{h["sim"]:.2f}</span>'
            f'<span><span class="mm-bar"><span style="width:{max(0, min(1, h["sim"])) * 100:.0f}%"></span></span>'
            f'<b>{esc(BOOKS.get(h["book"], h["book"]))}</b> · {esc(tidy_path(h["where"]))}</span></li>'
            for h in s.data["hits"][:5])
        extra = (f'<div class="mm-detail">Query: <span class="mm-q">{esc(s.data.get("query", ""))}</span> '
                 f'· top {len(s.data["hits"])} by cosine similarity</div><ul class="mm-hits">{rows}</ul>')
        detail = ""
    elif s.stage == "llm":
        d = s.data
        detail = (f'{esc(s.detail)} · ~{d.get("approx_tokens_in", 0):,} tokens in, '
                  f'~{d.get("approx_tokens_out", 0):,} out · temperature {d.get("temperature", 0)}')
    else:
        detail = esc(s.detail)
    ms = f'{s.ms / 1000:.1f} s' if s.ms >= 1000 else (f'{s.ms:.0f} ms' if s.ms >= 1 else "")
    return (f'<li class="mm-step {s.status}"><div class="mm-dot">{s.icon}</div>'
            f'<div class="mm-body"><div class="mm-stage">{esc(stage_label)}</div>'
            f'<div class="mm-title-s">{esc(s.title)}</div>'
            + (f'<div class="mm-detail">{detail}</div>' if detail else "") + extra +
            f'</div><div class="mm-ms">{ms}</div></li>')


def render_process(steps, total_ms) -> None:
    n_search = sum(s.stage == "retrieve" for s in steps)
    n_llm = sum(s.stage == "llm" for s in steps)
    st.markdown(f'<span class="mm-pill info">{len(steps)} steps</span>'
                f'<span class="mm-pill info">{n_search} textbook search{"es" if n_search != 1 else ""}</span>'
                f'<span class="mm-pill info">{n_llm} model call{"s" if n_llm != 1 else ""}</span>'
                f'<span class="mm-pill info">{total_ms / 1000:.1f} s total</span>', unsafe_allow_html=True)
    st.markdown('<ol class="mm-tl">' + "".join(step_html(s) for s in steps) + "</ol>", unsafe_allow_html=True)


def render_sources(res) -> None:
    p = res.plan
    if p is not None and getattr(p, "graph_facts", None):
        st.markdown('<div class="mm-label">Graph facts · Eka Care BODHI (CC BY-NC 4.0) and textbook ontology</div>',
                    unsafe_allow_html=True)
        for j, f in enumerate(p.graph_facts, 1):
            mark = " ✅" if j in res.graph_cited else ""
            st.markdown(f"**[G{j}]** {f}{mark}")
    if p is not None and getattr(p, "nav_hints", None):
        st.markdown('<div class="mm-label" style="margin-top:.6rem">Graph hints · not from the textbooks, not used in '
                    'the answer</div>', unsafe_allow_html=True)
        for h in p.nav_hints:
            st.caption(h)
    if p is not None and (getattr(p, "graph_facts", None) or getattr(p, "nav_hints", None)):
        st.markdown('<div class="mm-label" style="margin-top:.6rem">Textbook passages</div>', unsafe_allow_html=True)
    if res.hits and not res.cited:
        st.caption("None of the retrieved passages were cited in the answer.")
    for i, h in enumerate(res.hits, 1):
        cited = i in res.cited
        book = BOOKS.get(h.meta.get("book_id"), h.meta.get("book", ""))
        ex = h.passage[:300] + ("…" if len(h.passage) > 300 else "")
        st.markdown(
            f'<div class="mm-src{" cited" if cited else ""}"><div class="mm-src-head">'
            f'<span class="mm-src-n">[{i}]</span>'
            f'<span class="mm-pill {"good" if cited else "info"}">{"cited" if cited else "retrieved"}</span>'
            f'<span class="mm-pill info">{esc(book)}</span>'
            f'<span class="mm-pill info">match {h.similarity:.2f}</span></div>'
            f'<div class="mm-src-where">{esc(tidy_path(h.citation().removeprefix(h.meta.get("book", "") + ", ")))}</div>'
            f'<div class="mm-src-ex">{esc(ex)}</div></div>', unsafe_allow_html=True)
        if h.meta.get("book_id") == "grays":                       # a Gray's section on a drawn structure
            t3d = _safe(lambda: atlas.for_section(h.meta))
            if t3d:
                st.caption(f"🧍 [View {esc(t3d['label'])} in 3D]({t3d['url']})")


def _cg_click(key: str, conds: list[str]) -> None:
    """Graph click (runs before the rerun): a click on a candidate condition drills one level deeper; a click on a
    textbook differential adds it as a candidate; any click selects the node/edge for the inspector."""
    v, s = st.session_state.get(key), st.session_state[f"{key}_state"]
    if not v or v.get("nonce") == s["nonce"]:
        return
    s["nonce"], s["selected"] = v["nonce"], (v["kind"], v["id"])
    if v["kind"] == "node" and v["id"].startswith("condition:"):
        name = next((c for c in conds + s["extra"] if f"condition:{c.strip().lower()}" == v["id"]), None)
        if name is None:                                     # a differential: promote it to a candidate
            name = s["labels"].get(v["id"], v["id"].split(":", 1)[1])
            s["extra"].append(name)
        g = clinical_graph.build([], [name])
        s["depth"][name] = clinical_graph.next_depth(s["depth"].get(name, 2), g["levels"].get(name, []))
        s["focus"] = name


def render_clinical_graph(symptoms: list[str], conditions: list[str], key: str, height: int = 700) -> None:
    """Five-level clinical graph (complaints → differential → phases → workup → therapy) from certified facts."""
    if not onto.available() or not conditions:
        return
    s = st.session_state.setdefault(f"{key}_state", {"depth": {}, "extra": [], "selected": None, "nonce": None,
                                                     "focus": None, "labels": {}})
    conds = list(dict.fromkeys(conditions + s["extra"]))[:clinical_graph.CAPS["conditions"]]
    g = clinical_graph.build(symptoms, conds, s["depth"])
    s["labels"] = {n["id"]: n["label"] for n in g["nodes"]}
    focus = s["focus"] if s["focus"] in conds else conds[0]
    shown = max(s["depth"].get(focus, 2), 2)
    avail = {1, 2, *g["levels"].get(focus, [])}
    crumbs = "".join(
        f'<span class="mm-pill {"good" if lv <= shown else "info"}" style="opacity:{1 if lv <= shown else .5}">'
        f'{"✓ " if lv <= shown else ""}{lv} · {name}{"" if lv in avail else " (none in ontology)"}</span>'
        for lv, name in enumerate(clinical_graph.LEVELS, 1))
    st.markdown(f'<div class="mm-label">Clinical graph · {esc(focus)}</div>{crumbs}', unsafe_allow_html=True)
    rows = max(Counter(n["level"] for n in g["nodes"]).values(), default=1)
    height = min(height, max(300, 100 + 58 * rows))          # tallest column decides the height
    clinical_graph_view(g, key=key, height=height, on_change=functools.partial(_cg_click, key, conds))

    c1, c2, c3, _ = st.columns([1, 1, 1, 3])
    nxt = clinical_graph.next_depth(shown, g["levels"].get(focus, []))
    if c1.button(f"Drill in: {clinical_graph.LEVELS[nxt - 1]}" if nxt > shown else "Collapse",
                 key=f"{key}_drill", use_container_width=True, disabled=not g["levels"].get(focus)):
        s["depth"][focus] = nxt
        st.rerun()
    if c2.button("Show all 5 levels", key=f"{key}_all", use_container_width=True):
        s["depth"] = {c: 5 for c in conds}
        st.rerun()
    if c3.button("Reset", key=f"{key}_reset", use_container_width=True):
        s.update(depth={}, extra=[], selected=None, focus=None)
        st.rerun()

    sel = s["selected"]
    if sel and sel[0] == "edge":
        e = next((e for e in g["edges"] if e["id"] == sel[1]), None)
        f = g["facts"].get(e["fact"]) if e else None
        if f:
            cf = f.get("clinical_facets") or {}
            extra = " · ".join(x for x in (
                onto.LINE_LABEL.get(cf.get("line_of_therapy")) if cf.get("line_of_therapy") else "",
                f"{cf['contraindication_severity'].lower()} contraindication" if cf.get("contraindication_severity") else "",
                f"Why: {cf['rationale']}" if cf.get("rationale") else "") if x)
            quote = (f.get("provenance") or {}).get("verbatim_quote") or ""
            st.markdown(
                f'<div class="mm-src cited"><div class="mm-src-head"><span class="mm-pill good">certified fact</span>{corr_badge(f)}'
                f'<span class="mm-src-where"><b>{esc(f["subject_label"])} → {esc(f["predicate"])} → '
                f'{esc(f["object_label"])}</b></span></div><div class="mm-src-ex">{esc(f.get("nl_fact", ""))}</div>'
                + (f'<div class="mm-src-ex">{esc(extra)}</div>' if extra else "")
                + f'<div class="mm-src-where" title="{esc(cite_text(f))}">📖 {esc(cite_text(f))}</div>'
                + (f'<div class="mm-src-ex"><i>“{esc(quote)}”</i></div>' if quote else "") + "</div>",
                unsafe_allow_html=True)
        elif e:
            st.caption(f"{s['labels'].get(e['from'], '')} → {s['labels'].get(e['to'], '')}: linked by the symptom "
                       "graph only; no certified textbook fact states this link.")
    elif sel and sel[0] == "node":
        n = next((n for n in g["nodes"] if n["id"] == sel[1]), None)
        if n and n["kind"] != "condition":
            links = [e for e in g["edges"] if sel[1] in (e["from"], e["to"]) and e["fact"]]
            st.caption(f"**{n['label']}** · {n['title']} · {len(links)} cited link(s). Click a line for its source.")


def render_answer(res, steps, total_ms, key: str = "", question: str = "") -> None:
    label, tone = STATUS[res.status]
    route = ROUTE.get(res.plan.route) if res.plan is not None else None
    pills = f'<span class="mm-pill {tone}">{label}</span>'
    if route:
        pills += f'<span class="mm-pill info">{route}</span>'
    st.markdown(f'<div class="mm-pills">{pills}</div>', unsafe_allow_html=True)
    st.markdown(res.text)
    conds = getattr(res.plan, "conditions", None) if res.plan is not None else None
    if key and question:      # on-demand Graphviz flowchart from certified facts; renders nothing when n/a
        diagrams.render(st, question, res.text, condition=(conds or [None])[0], key=f"diagram_{key}")
    if conds and key and onto.available():
        with st.expander("🕸️  Clinical graph · complaints → differential → phases → workup → therapy", expanded=True):
            render_clinical_graph(getattr(res.plan, "symptoms", []), conds, key=f"cg_{key}")
    if steps:
        with st.expander(f"🔬  How this answer was made · {len(steps)} steps · {total_ms / 1000:.1f} s", expanded=False):
            render_process(steps, total_ms)
    if res.hits or (res.plan is not None and getattr(res.plan, "graph_facts", None)):
        with st.expander(f"📚  Sources · {len(res.cited)} cited of {len(res.hits)} retrieved"):
            render_sources(res)


# ---------------------------------------------------------------- Ask tab
with tab_ask:
    st.session_state.setdefault("messages", [])
    with st.expander("Try a demo question", expanded=not st.session_state.messages):
        cols = st.columns(3)
        for n, (kind, q) in enumerate(EXAMPLES):
            with cols[n % 3]:
                st.markdown(f'<div class="mm-label">{kind}</div>', unsafe_allow_html=True)
                if st.button(q, key=f"ex{n}", use_container_width=True):
                    st.session_state.pending = q

    hint = st.empty()   # cleared as soon as a question arrives this run
    if not st.session_state.messages:
        hint.markdown('<div class="mm-empty">No questions yet. Pick a demo question above or type your own below. '
                      'Each answer lists its textbook sources and can show how it was made.</div>', unsafe_allow_html=True)
    for i, m in enumerate(st.session_state.messages):
        with st.chat_message(m["role"], avatar="🧑‍⚕️" if m["role"] == "user" else "🩺"):
            if m["role"] == "user":
                st.markdown(m["content"])
            else:
                render_answer(m["result"], m["steps"], m["ms"], key=f"m{i}",
                              question=st.session_state.messages[i - 1]["content"] if i else "")

    question = st.chat_input("Ask a medicine, pharmacology, pathology, physiology or microbiology question…")
    question = question or st.session_state.pop("pending", None)
    if question:
        hint.empty()
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user", avatar="🧑‍⚕️"):
            st.markdown(question)
        with st.chat_message("assistant", avatar="🩺"):
            box = st.status("Working through the pipeline…", expanded=True)

            def live(s):
                box.markdown(f"{s.icon} **{s.title}**" + (f" · {s.detail[:110]}" if s.detail and s.stage != "llm" else ""))

            tr = trace.start(live)
            try:
                if retriever != "vector":
                    res = answer(question, retriever=retriever)
                else:
                    res = answer_multihop(question) if multihop else answer(question)
            except RuntimeError as e:         # LLM backend down, model missing, STAIR not installed
                trace.stop()
                box.update(label="Could not answer", state="error")
                st.warning(str(e))
                st.stop()
            except Exception as e:            # never show a raw traceback in the demo
                trace.stop()
                box.update(label="Could not answer", state="error")
                st.error(f"Something went wrong while answering ({type(e).__name__}). Please try again.")
                st.stop()
            trace.stop()
            total = tr.total_ms
            box.update(label=f"Done · {len(tr.steps)} steps in {total / 1000:.1f} s", state="complete", expanded=False)
            render_answer(res, tr.steps, total, key=f"m{len(st.session_state.messages)}", question=question)
        st.session_state.messages.append({"role": "assistant", "content": res.text, "result": res,
                                          "steps": tr.steps, "ms": total})


# ---------------------------------------------------------------- How it works tab
with tab_how:
    st.markdown("### From a question to a cited answer")
    st.markdown("MedEvolv Mentor is a **retrieval-augmented** assistant: it never answers from the language model's "
                "memory. It first finds evidence in the textbooks (and, for clinical cases, in a medical knowledge "
                "graph), then asks the model to write an answer **using only that evidence**, citing each claim. "
                "If the evidence isn't there, it says so instead of guessing.")
    NODE = ('node [shape=box, style="rounded,filled", fillcolor="#ffffff", color="#c9d6d8", fontname="Helvetica", '
            'fontsize=15, margin="0.2,0.1"]; edge [color="#7a9097", arrowsize=0.7, fontname="Helvetica", fontsize=12];')
    st.markdown('<div class="mm-label">At question time</div>', unsafe_allow_html=True)
    st.graphviz_chart("""
digraph Q { rankdir=LR; bgcolor="transparent"; nodesep=0.3; ranksep=0.45; """ + NODE + """
  q [label="Your question", fillcolor="#15232a", fontcolor="#ffffff", color="#15232a"];
  guard [label="Safety\\ncheck"]; route [label="Route"];
  case [label="Clinical case\\n(graph hops)"]; comp [label="Compound\\n(split)"]; single [label="Single\\nsearch"];
  search [label="Search textbooks\\n+ relevance filter"]; llm [label="Model writes from\\nevidence only"];
  out [label="Cited answer\\n+ full trace", fillcolor="#e3f3ea", color="#9cc9ad"];
  refuse [label="Decline", fillcolor="#f8e3e4", color="#e0a8ac"];
  bodhi [label="BODHI graph", fillcolor="#e2f0f1"];
  q -> guard -> route; route -> case; route -> comp; route -> single;
  case -> search; comp -> search; single -> search; bodhi -> case [style=dashed];
  search -> llm -> out;
  guard -> refuse [style=dashed, label="personal"]; search -> refuse [style=dashed, label="no evidence"];
}""", use_container_width=True)
    st.markdown('<div class="mm-label">Built once, offline</div>', unsafe_allow_html=True)
    st.graphviz_chart("""
digraph B { rankdir=LR; bgcolor="transparent"; nodesep=0.3; ranksep=0.45; """ + NODE + """
  pdf [label="7 textbook\\nPDFs"]; toc [label="Recover contents\\n2,611 sections"];
  chunk [label="~250-word passages\\n36,725"]; emb [label="Embed\\n(bge-small)"];
  db [label="Vector database\\n(Chroma)", fillcolor="#e2f0f1"];
  pdf -> toc -> chunk -> emb -> db;
}""", use_container_width=True)

    st.markdown("#### What happens to every question")
    stages = [
        ("1", "🛡️ Safety check", "Questions asking for dosing or treatment of a real person (\"my mother has TB…\") "
         "are declined before anything is searched. It is a study aid, not a doctor."),
        ("2", "🧭 Routing", "A clinical vignette (two or more symptoms, or \"a patient presents with…\") goes to the "
         "knowledge graph. A question about several things (\"compare X and Y\") is split into parts. Everything "
         "else is a single search."),
        ("3", "🕸️ Knowledge graph", "Symptoms are matched to nodes in Eka Care's open BODHI graph, which ranks "
         "likely conditions and links them to specialists and drugs. The graph proposes; the textbooks confirm."),
        ("4", "📖 Textbook search", "The question (or each part) is turned into a vector and compared with all 36,725 "
         "passages. The closest ones are kept, and passages about a condition must actually name it."),
        ("5", "🤖 Grounded answer", "The model receives numbered evidence and strict rules: answer only from it, "
         "cite every claim as [n] or [G n], and reply INSUFFICIENT_CONTEXT if the evidence doesn't answer it."),
        ("6", "🔎 Checks", "Citations are verified against the evidence list, and drugs in the answer are cross-checked "
         "against the graph's drug links. Every step is recorded and shown under the answer."),
    ]
    for row in (stages[:3], stages[3:]):
        cols = st.columns(3)
        for col, (n, title, body) in zip(cols, row):
            with col:
                st.markdown(f'<div class="mm-card"><span class="mm-num">STEP {n}</span><h4>{title}</h4>'
                            f'<p>{body}</p></div>', unsafe_allow_html=True)
        st.write("")

    st.markdown("**Two newer additions.** Long clinical cases (35+ words) take a *case route*: the model splits the case "
                "along up to three clinical axes (cause and diagnosis, emergency stabilisation, drug treatment), searches "
                "short textbook-style queries for each alongside the whole case, and answers axis by axis. "
                f"A **clinical ontology** (facts extracted by a language model from {onto_sections():,} textbook sections) adds "
                "first-line drugs, confirmatory tests and contraindication warnings to answers. A fact is kept only if "
                "its quote is found word-for-word in the source, and a second model pass checks that the quote actually states "
                "the fact; reversed or mistyped facts are corrected or dropped, "
                "and a first-line tag is removed when the source hedges. The quote is verified, not the medical "
                "judgement, so check the source before relying on a fact. Browse it in the *Explore conditions* tab.")
    left, right = st.columns(2)
    with left:
        st.markdown("#### Three ways it says no")
        st.markdown("- **Personal advice** → declined up front, no search.\n"
                    f"- **Weak evidence** → if the best passage scores below **{config.MIN_SIMILARITY:.2f}** "
                    "similarity, the model is never called.\n"
                    "- **Model check** → if the passages don't actually answer it, the model must say so "
                    "(INSUFFICIENT_CONTEXT) and the bot declines.")
        st.markdown("#### Sources")
        st.markdown("| Source | Subject | Sections |\n|---|---|---|\n"
                    "| KD Tripathi, Essentials of Medical Pharmacology 7e | Pharmacology | 447 |\n"
                    "| Guyton & Hall, Textbook of Medical Physiology 14e | Physiology | 478 |\n"
                    "| Davidson's Principles and Practice of Medicine 24e | Medicine | 338 |\n"
                    "| Robbins & Cotran, Pathologic Basis of Disease | Pathology | 212 |\n"
                    "| Microbiology textbook | Microbiology | 82 |\n"
                    "| Harrison's Principles of Internal Medicine 22e | Internal Medicine | 505 |\n"
                    "| Gray's Anatomy for Students 5e | Anatomy | 549 |\n"
                    "| Eka Care BODHI-S + BODHI-M (CC BY-NC 4.0) | Clinical graph | 6,560 nodes |")
    with right:
        st.markdown("#### How well it works")
        st.markdown("Tested on 39 questions covering every type (22 factual, 3 comparison, 5 clinical cases, "
                    "5 off-topic, 4 personal-advice), with multi-hop on (13 Nov):")
        st.markdown("| Measure | Result |\n|---|---|\n"
                    "| Right behaviour (answer / decline / refuse) | **39 / 39** |\n"
                    "| Cited passage from the right textbook | **23 / 25** |\n"
                    "| Answers with at least one citation | **30 / 30** |\n"
                    "| Answers fully grounded in their cited passages | **30 / 30** |\n"
                    "| Correct chapter as top search result (446 questions) | **76.5%** |\n"
                    "| Correct chapter in top 3 | **90.8%** |\n"
                    "| Typical answer time | **~3 s** |")
        st.markdown("#### Known limits")
        st.markdown("- Hard multi-part clinical cases cover about 83% of an examiner's key points on average "
                    "(pharmacology parts are weakest); the trace shows which parts were found.\n"
                    "- Anatomy is new: in a 10-question check, 9 were answered and 8 cited Gray's; some topics "
                    "(e.g. Erb's palsy) are not yet found.\n"
                    "- Answers are only as complete as the seven indexed books.\n"
                    "- A study aid for students, not clinical decision support.")
    st.markdown("#### Built with")
    st.markdown(" ".join(f'<span class="mm-chip">{t}</span>' for t in
                         ["Python", "Streamlit", "Chroma", "bge-small-en-v1.5", "DeepSeek", "networkx",
                          "PyMuPDF", "Oracle Cloud", "Caddy"]), unsafe_allow_html=True)


# ---------------------------------------------------------------- Explore conditions tab
def fact_row(f, uid: str, arrow: bool = False) -> None:
    """One compact card for a certified fact, plus a 'Source' expander with the (truncated) verbatim quote."""
    name = f"{f['subject_label']} → {f['object_label']}" if arrow else f["object_label"]
    cf = f.get("clinical_facets") or {}
    sev = cf.get("contraindication_severity")
    pill = ('<span class="mm-pill bad">strict</span>' if sev == "STRICT"
            else '<span class="mm-pill warn">caution</span>' if sev == "CAUTIONARY" else "") + corr_badge(f)
    if f["predicate"] == "CONTRAINDICATES":
        # scoped wording ("... when the patient is pregnant: <why>") so subgroup cautions never read as blanket bans
        try:
            body, why = onto.warning_text(f), ""
        except Exception:
            body = f.get("nl_fact", "")
            why = f'<div class="mm-src-ex">Why: {esc(cf["rationale"])}</div>' if cf.get("rationale") else ""
    else:
        body, why = f.get("nl_fact", ""), ""
    st.markdown(f'<div class="mm-src"><div class="mm-src-head">{pill}<span class="mm-src-where"><b>{esc(name)}</b></span></div>'
                f'<div class="mm-src-ex">{esc(body)}</div>{why}</div>', unsafe_allow_html=True)
    quote = (f.get("provenance") or {}).get("verbatim_quote") or ""
    quote = quote[:300] + ("…" if len(quote) > 300 else "")
    with st.expander("Source"):
        st.caption(cite_text(f))
        if quote:
            st.markdown(f"> {quote}")


def _book_cite(f, book: str) -> str:
    for p in onto.sources(f):
        if p.get("book_id") == book:
            return onto.cite({"provenance": p})
    return onto.cite(f)


def books_differ(items) -> None:
    """Neutral, collapsed note where textbooks give different recommendations; shows both sides."""
    with st.expander(f"Books differ · {len(items)} case{'s' if len(items) != 1 else ''}", expanded=False):
        st.caption("These textbooks give different recommendations. Neither is marked wrong, so read both sources.")
        for c in items:
            fs = c.get("facts") or []
            if c.get("kind") == "first_line_differs":
                sides = ""
                for b, drugs in (c.get("by_book") or {}).items():
                    src = next((f for f in fs if b in onto.books(f)), None)
                    sides += (f'<div class="mm-side"><b>{esc(BOOKS.get(b, b))}</b>: {esc(", ".join(drugs))}'
                              + (f'<br>📖 {esc(_book_cite(src, b))}' if src else "") + '</div>')
                st.markdown(f'<div class="mm-differ"><div><b>{esc(c["condition"])}</b>: first-line drugs differ between books</div>'
                            f'{sides}</div>', unsafe_allow_html=True)
            else:
                sides = ""
                for f in fs:
                    role = "Listed as a treatment" if f["predicate"] == "TREATED_BY" else "Listed as a contraindication"
                    quote = (f.get("provenance") or {}).get("verbatim_quote") or ""
                    quote = quote[:240] + ("…" if len(quote) > 240 else "")
                    sides += (f'<div class="mm-side"><b>{role}</b> · {esc(cite_text(f))}'
                              + (f'<br><i>“{esc(quote)}”</i>' if quote else "") + '</div>')
                st.markdown(f'<div class="mm-differ"><div><b>{esc(c.get("drug", ""))}</b> in {esc(c["condition"])}: '
                            f'recommendation depends on the source (often a subgroup or timing nuance)</div>'
                            f'{sides}</div>', unsafe_allow_html=True)


def fact_list(facts_, uid: str, arrow: bool = False) -> None:
    for i, f in enumerate(by_corroboration(facts_)):
        fact_row(f, f"{uid}{i}", arrow)


# ---- concept pages (Stage 7 of docs/graph_networking_plan.md): search, backlinks, related, mentions, local graph.
# Everything here is navigation. Certified facts are stated from the concept's own side; the "Linked from" list is the
# same facts read backwards (tagged "derived"); the book sections are mentions and are never shown as clinical edges.
try:
    from rag import concepts as _concepts
except Exception:                       # pragma: no cover - optional layer
    _concepts = None
try:
    from rag import mentions as _mentions
except Exception:                       # pragma: no cover - optional layer
    _mentions = None

try:
    from rag import hubs as _hubs
except Exception:                       # pragma: no cover - optional layer
    _hubs = None
try:
    from rag import crosswalk as _crosswalk
except Exception:                       # pragma: no cover - optional layer
    _crosswalk = None
try:
    from rag import comention as _comention
except Exception:                       # pragma: no cover - optional layer
    _comention = None

TYPE_NAME = {"PathologicalCondition": "Condition", "ClinicalPhenotype": "Symptom / finding",
             "TherapeuticAgent": "Drug / therapy", "DiagnosticModality": "Test", "PhysiologicalProcess": "Process",
             "EtiologicalAgent": "Cause / organism", "ClinicalStage": "Stage", "MolecularTarget": "Target",
             "OrganSystem": "Organ system", "AnatomicalStructure": "Anatomical structure"}
TYPE_FILL = {"PathologicalCondition": "#f6c9c4", "ClinicalPhenotype": "#fbe3a6", "TherapeuticAgent": "#bfe3c8",
             "DiagnosticModality": "#c4daf3", "PhysiologicalProcess": "#e0d0f0", "EtiologicalAgent": "#f5d2b3",
             "ClinicalStage": "#d9dde0", "MolecularTarget": "#bfe6e3", "OrganSystem": "#d9dde0",
             "AnatomicalStructure": "#d8cbb8"}
PRED_TEXT = {"TREATED_BY": "treated by", "CONTRAINDICATES": "contraindicates", "MANIFESTS_AS": "manifests as",
             "CONFIRMED_BY": "confirmed by", "CAUSED_BY": "caused by", "DISRUPTS_PATHWAY": "disrupts",
             "CAUSES_ADVERSE_EFFECT": "causes adverse effect", "HAS_CLINICAL_STAGE": "has stage",
             "TARGETS_MECHANISM": "targets", "DIFFERENTIAL_OF": "differential of", "is_a": "is a",
             "INVOLVES_STRUCTURE": "involves structure"}
GRAPH_CAP = {1: 24, 2: 40}

st.html("""<style>
.mm-mention { border:1px dashed var(--line); border-radius:10px; padding:.6rem .85rem; margin:.3rem 0 .6rem; color:var(--muted); }
.mm-mention .mm-mn { font-size:.86rem; line-height:1.4; padding:.1rem 0; overflow-wrap:anywhere; }
.mm-mention .mm-mn small { display:block; font-size:.76rem; opacity:.85; }
.mm-grp { font-weight:600; color:var(--ink); margin:.5rem 0 .15rem; }
.mm-grp .mm-pill { font-weight:500; margin-left:.4rem; opacity:.85; }
.mm-trail { font-size:.86rem; color:var(--muted); overflow-wrap:anywhere; margin:.2rem 0 .4rem; }
.mm-trail b { color:var(--ink); }
.mm-pill.sug { background:transparent; color:var(--muted); border:1px dashed var(--line); font-size:.68rem; padding:.05rem .45rem; cursor:help; }
.mm-pill.tier { background:transparent; color:var(--muted); border:1px solid var(--line); font-size:.68rem; padding:.05rem .45rem; cursor:help; }
.mm-xw { font-size:.9rem; color:var(--ink); line-height:1.7; overflow-wrap:anywhere; margin:.1rem 0; }
.mm-xw.mute, .mm-xw.mute .mm-label { color:var(--muted); }
.mm-xw .mm-label { margin-right:.4rem; }
.mm-hubnode { display:inline-block; width:.8rem; height:.8rem; background:#e9eef0; border:1.5px solid #7d8f95; vertical-align:middle; margin-right:.3rem; }
[class*="_seealso"] { background:var(--accent-soft); border-radius:10px; padding:.1rem .4rem; margin:.4rem 0; }
[class*="_seealso"] summary, [class*="_seealso"] button, [class*="_seealso"] p { color:var(--muted); }
.mm-hubpg { font-size:.84rem; color:var(--muted); margin:.1rem 0; }
</style>""")


@st.cache_data(show_spinner=False, max_entries=256)
def _c_page(cid: str) -> dict:
    return _concepts.concept(cid) if _concepts else {}


@st.cache_data(show_spinner=False, max_entries=256)
def _c_related(cid: str, k: int = 12) -> list:
    return _concepts.related(cid, k=k) if _concepts else []


@st.cache_data(show_spinner=False, max_entries=256)
def _c_search(q: str) -> list:
    return _concepts.search_concepts(q, limit=10) if _concepts else []


@st.cache_data(show_spinner=False, max_entries=256)
def _c_sections(label: str) -> list:
    return _mentions.sections_for(label, k=8) if _mentions else []


@st.cache_data(show_spinner=False, max_entries=256)
def _h_for(label: str) -> list:
    return _hubs.hubs_for(label) if _hubs else []


@st.cache_data(show_spinner=False, max_entries=64)
def _h_members(hub_id: str) -> list:
    return _hubs.members(hub_id, k=100000) if _hubs else []


@st.cache_data(show_spinner=False, max_entries=256)
def _x_bodhi(label: str) -> list:
    return _crosswalk.bodhi_for(label, relations=("exact", "broader", "narrower", "related")) if _crosswalk else []


@st.cache_data(show_spinner=False, max_entries=256)
def _sa(label: str) -> list:
    return _comention.see_also(label, 10) if _comention else []


def _dot_text(s: str, n: int = 30) -> str:
    s = s if len(s) <= n else s[:n - 1].rstrip() + "…"
    return s.replace("\\", " ").replace('"', "'")


@st.cache_data(show_spinner=False, max_entries=128)
def _local_dot(cid: str, hops: int, hubs: bool = False) -> tuple[str, int, int]:
    """DOT for the neighbourhood of a concept (capped). Edges read from the concept outwards: solid = a certified fact
    stated from that end, dashed = the same fact read backwards (derived). Mention links and co-mention are never drawn.
    With hubs=True the concept's T2 hubs are added as square boxes on dotted edges. Returns (dot, concepts, hubs)."""
    cap = GRAPH_CAP.get(hops, 24)
    nodes: dict[str, tuple[str, str]] = {}
    edges: list[tuple[str, str, str, bool]] = []
    seen_facts: set[str] = set()

    def links_of(nid: str):
        c = _concepts.concept(nid)
        for pred, ls in c.get("outgoing", {}).items():
            for lk in ls:
                yield lk, PRED_TEXT.get(pred, pred), False
        for name, ls in c.get("backlinks", {}).items():
            for lk in ls:
                yield lk, name, True

    c0 = _concepts.concept(cid)
    if not c0:
        return "", 0, 0
    nodes[cid] = (c0["label"], c0["type"])
    ranked = [r["id"] for r in _concepts.related(cid, k=cap - 1)]
    keep = set(ranked)
    for lk, text, derived in links_of(cid):
        o = lk["other_id"]
        if o in keep and lk["fact_id"] not in seen_facts and o != cid:
            seen_facts.add(lk["fact_id"])
            nodes.setdefault(o, (lk["other_label"], lk["other_type"]))
            edges.append((cid, o, text, derived))
    if hops >= 2:
        for first in ranked[:10]:
            if len(nodes) >= cap:
                break
            added = 0
            for lk, text, derived in links_of(first):
                o = lk["other_id"]
                if lk["fact_id"] in seen_facts or o == cid or first not in nodes:
                    continue
                if o not in nodes and (len(nodes) >= cap or added >= 4):
                    continue
                seen_facts.add(lk["fact_id"])
                if o not in nodes:
                    nodes[o] = (lk["other_label"], lk["other_type"])
                    added += 1
                edges.append((first, o, text, derived))
    ids = {n: f"n{i}" for i, n in enumerate(nodes)}
    out = ['digraph G { bgcolor="transparent"; rankdir=LR; nodesep=0.18; ranksep=1.1; pad=0.1;',
           'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, fontcolor="#15232a", color="#7d8f95", margin="0.12,0.06"];',
           'edge [color="#7d8f95", fontcolor="#7d8f95", fontname="Helvetica", fontsize=9, arrowsize=0.7];']
    for n, (label, typ) in nodes.items():
        extra = ', penwidth=3, fontsize=13' if n == cid else ""
        out.append(f'{ids[n]} [label="{_dot_text(label)}", fillcolor="{TYPE_FILL.get(typ, "#d9dde0")}"{extra}];')
    for a, b, text, derived in edges:
        out.append(f'{ids[a]} -> {ids[b]} [label="{_dot_text(text, 26)}"{", style=dashed" if derived else ""}];')
    t2 = {}
    if hubs:
        t2 = {h["hub_id"]: h for h in _h_for(c0["label"]) if h["tier"] == "T2"}
        for i, h in enumerate(t2.values()):
            out.append(f'h{i} [label="{_dot_text(h["hub_label"])}", shape=box, style=filled, fillcolor="#e9eef0", '
                       'color="#7d8f95", penwidth=1.5];')
            out.append(f'{ids[cid]} -> h{i} [style=dotted, label="part of", arrowhead=none];')
    out.append("}")
    return "\n".join(out), len(nodes), len(t2)


def _go(cid: str) -> None:
    """Open a concept page; the page we leave is pushed on the breadcrumb trail."""
    cur = st.session_state.get("ex_cur")
    if cur and cur != cid:
        trail = st.session_state.setdefault("ex_trail", [])
        trail.append(cur)
        del trail[:-8]
    st.session_state["ex_cur"] = cid
    st.session_state["ex_hub"] = None                    # opening a concept always leaves a hub page


def _pick(key: str) -> None:
    """Callback of a chip group: open the chosen concept, then clear the chip so it can be chosen again later."""
    cid = st.session_state.get(key)
    st.session_state[key] = None
    if cid:
        if key == "ex_hit":
            st.session_state["ex_q"] = ""
        _go(cid)


def _back() -> None:
    trail = st.session_state.get("ex_trail") or []
    st.session_state["ex_cur"] = trail.pop() if trail else None
    st.session_state["ex_hub"] = None


def _home() -> None:
    st.session_state["ex_cur"], st.session_state["ex_trail"], st.session_state["ex_hub"] = None, [], None


def concept_chips(items: list[dict], key: str, fmt) -> None:
    """Clickable chips (navigation). items need an 'id'; fmt(item) gives the chip text."""
    by_id = {i["id"]: i for i in items}
    st.pills("Open concept", list(by_id), selection_mode="single", default=None, key=key, wrap=True,
             format_func=lambda i: fmt(by_id[i]), on_change=_pick, args=(key,), label_visibility="collapsed")


def _type_name(t: str) -> str:
    return TYPE_NAME.get(t, "Concept")


def render_concept_search() -> None:
    if _concepts is None:
        return
    st.markdown('<div class="mm-label">Search any concept</div>', unsafe_allow_html=True)
    q = st.text_input("Search concepts", key="ex_q", label_visibility="collapsed",
                      placeholder="A drug, test, symptom, organism or condition, e.g. Rifampin")
    if len(q.strip()) >= 2:
        hits = _safe(lambda: _c_search(q.strip()), [])
        if hits:
            concept_chips(hits, "ex_hit", lambda h: f"{h['label']} · {_type_name(h['type'])}")
        else:
            st.caption("No concept starts with that. Try the first letters of a name.")


def panel_links(c: dict, uid: str) -> None:
    """'Linked from': incoming facts grouped by their inverse predicate, plus 'Links to' for facts stated from here."""
    groups = c.get("backlinks") or {}
    if groups:
        st.markdown('<div class="mm-label">Linked from</div>', unsafe_allow_html=True)
        st.caption("Facts from other concepts that point here, read backwards. Each is the same certified fact as "
                   "in the textbooks (same source), so the \"derived\" tag adds no new claim.")
    for name, links in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        uniq = {}
        for lk in links:
            old = uniq.get(lk["other_id"])
            if old is None or len(lk["books"]) > len(old["books"]):
                uniq[lk["other_id"]] = {**lk, "id": lk["other_id"], "label": lk["other_label"]}
        items = sorted(uniq.values(), key=lambda x: (-len(x["books"]), x["label"]))
        st.markdown(f'<div class="mm-grp">{esc(name.capitalize())} · {len(links)}'
                    f'<span class="mm-pill info" title="The same certified fact read from the other side">derived</span></div>',
                    unsafe_allow_html=True)
        fmt = lambda x: x["label"] + (f" · {len(x['books'])} books" if len(x["books"]) > 1 else "")
        slug = re.sub(r"\W+", "_", name)
        concept_chips(items[:20], f"{uid}_bl_{slug}", fmt)
        if len(items) > 20:
            with st.expander(f"Show {min(len(items), 140) - 20} more"):
                concept_chips(items[20:140], f"{uid}_blx_{slug}", fmt)
    out = c.get("outgoing") or {}
    if out:
        st.markdown('<div class="mm-label" style="margin-top:.8rem">Links to</div>', unsafe_allow_html=True)
        st.caption("Certified facts stated from this concept's side.")
        for pred, links in sorted(out.items(), key=lambda kv: -len(kv[1])):
            uniq = {}
            for lk in links:
                old = uniq.get(lk["other_id"])
                if old is None or len(lk["books"]) > len(old["books"]):
                    uniq[lk["other_id"]] = {**lk, "id": lk["other_id"], "label": lk["other_label"]}
            items = sorted(uniq.values(), key=lambda x: (-len(x["books"]), x["label"]))
            st.markdown(f'<div class="mm-grp">{esc(PRED_TEXT.get(pred, pred).capitalize())} · {len(links)}</div>',
                        unsafe_allow_html=True)
            fmt = lambda x: x["label"] + (f" · {len(x['books'])} books" if len(x["books"]) > 1 else "")
            slug = re.sub(r"\W+", "_", pred)
            concept_chips(items[:20], f"{uid}_ol_{slug}", fmt)
            if len(items) > 20:
                with st.expander(f"Show {min(len(items), 140) - 20} more"):
                    concept_chips(items[20:140], f"{uid}_olx_{slug}", fmt)


def panel_related(c: dict, uid: str) -> None:
    rel = _c_related(c["id"], 12)
    if not rel:
        return
    st.markdown('<div class="mm-label">Related concepts</div>', unsafe_allow_html=True)
    st.caption("Direct neighbours, ranked by how many certified facts join them. A way to explore, not a statement.")
    concept_chips(rel, f"{uid}_rel", lambda r: f"{r['label']} · {_type_name(r['type'])}")


def panel_mentions(c: dict) -> None:
    secs = _c_sections(c["label"])
    if not secs:
        return
    by_book: dict[str, list] = {}
    for s in secs:
        by_book.setdefault(s["book_id"], []).append(s)
    body = ""
    for b, rows in by_book.items():
        body += f'<div class="mm-label" style="margin-top:.35rem">{esc(BOOKS.get(b, b))}</div>'
        for s in rows:
            parent = tidy_path(" › ".join(s["path"][:-1])) if len(s.get("path") or []) > 1 else ""
            body += f'<div class="mm-mn">{esc(s["title"])}' + (f"<small>{esc(parent)}</small>" if parent else "") + "</div>"
    st.markdown('<div class="mm-label">Where the books discuss this</div>'
                '<div class="mm-mention"><div class="mm-mn"><i>Mentions · navigation only, not a clinical claim. '
                "These sections name the concept; they do not say what it treats, causes or confirms.</i></div>"
                f"{body}</div>", unsafe_allow_html=True)


SUGGESTED_TIP = "Grouping suggested by a model and checked against a shared textbook section; not a textbook statement."
HUB_GROUPS = (("Organ system", ("organ_system",)), ("Drug class", ("drug_class",)), ("Mechanism", ("mechanism",)),
              ("Organism family / genus", ("organism_genus", "organism_family")), ("Kind of", ("condition_hierarchy",)))
HUB_KIND = {"organ_system": "Organ system", "drug_class": "Drug class", "mechanism": "Mechanism",
            "organism_genus": "Organism genus", "organism_family": "Organism family", "condition_hierarchy": "Kind of"}
SUG_TAG = f'<span class="mm-pill sug" title="{html.escape(SUGGESTED_TIP)}">suggested</span>'
HUB_PAGE = 30


def _open_hub(key: str) -> None:
    hid = st.session_state.get(key)
    st.session_state[key] = None
    if hid:
        st.session_state["ex_hub"], st.session_state["ex_hub_page"] = hid, 0


def panel_part_of(c: dict, uid: str) -> None:
    """'Part of': the concept's hubs as chips grouped by kind. Navigation only; T3 groupings carry a 'suggested' tag."""
    found = {}
    for h in _h_for(c["label"]):
        found.setdefault(h["hub_id"], h)
    if not found:
        return
    st.markdown('<div class="mm-label">Part of</div>', unsafe_allow_html=True)
    any_t3 = False
    for title, kinds in HUB_GROUPS:
        items = [{"id": h["hub_id"], **h} for h in found.values() if h["hub_type"] in kinds]
        if not items:
            continue
        t3 = any(i["tier"] == "T3" for i in items)
        any_t3 = any_t3 or t3
        st.markdown(f'<div class="mm-grp">{esc(title)}' + (SUG_TAG if t3 else "") + "</div>", unsafe_allow_html=True)
        by_id = {i["id"]: i for i in items}
        mixed = len({i["tier"] for i in items}) > 1
        st.pills("Open group", list(by_id), selection_mode="single", default=None, key=f"{uid}_hub_{kinds[0]}", wrap=True,
                 format_func=lambda i: by_id[i]["hub_label"] + (" · suggested" if mixed and by_id[i]["tier"] == "T3" else ""),
                 on_change=_open_hub, args=(f"{uid}_hub_{kinds[0]}",), label_visibility="collapsed")
    st.caption("Groups for browsing. Being listed in a group does not mean facts about the group apply to this concept."
               + (" Tagged groupings are suggested by a model and checked against a shared textbook section; "
                  "not a textbook statement." if any_t3 else ""))


REL_TEXT = {"exact": ("same concept", "The BODHI record names the same concept"),
            "broader": ("broader", "The BODHI record is a more general concept"),
            "narrower": ("narrower", "The BODHI record is a more specific concept"),
            "related": ("related", "A nearby concept in BODHI")}
TIER_TIP = {"T2": "Derived by a deterministic rule over curated data", "T3": "Suggested by a model; not checked"}


def _bodhi_line(r: dict) -> str:
    txt, tip = REL_TEXT.get(r["relation"], (r["relation"], ""))
    mute = " mute" if r["tier"] == "T3" else ""
    return (f'<div class="mm-xw{mute}">{esc(r["bodhi_name"])} '
            f'<span class="mm-pill info" title="{esc(tip)}">{esc(txt)}</span>'
            f'<span class="mm-pill tier" title="{esc(TIER_TIP.get(r["tier"], ""))}">{esc(r["tier"])}</span></div>')


def panel_bodhi(c: dict, uid: str) -> None:
    rows = _x_bodhi(c["label"])
    main = [r for r in rows if r["relation"] != "related"][:4]
    more = [r for r in rows if r["relation"] == "related"][:8]
    if not main and not more:
        return
    st.markdown('<div class="mm-label">Also in BODHI</div>', unsafe_allow_html=True)
    if main:
        st.markdown("".join(_bodhi_line(r) for r in main), unsafe_allow_html=True)
    else:
        st.caption("No same, broader or narrower BODHI record.")
    if more:
        with st.expander(f"more · {len(more)} related"):
            st.markdown("".join(_bodhi_line(r) for r in more), unsafe_allow_html=True)
    st.caption("BODHI is a separate knowledge graph (CC BY-NC 4.0). A match means two records name the same or a "
               "nearby thing; it is not a clinical claim.")


def panel_see_also(c: dict, uid: str) -> None:
    rows = _sa(c["label"])
    items, seen = [], set()
    for r in rows:
        tgt = _safe(lambda r=r: _c_page(r["label"]), {})
        if tgt and tgt["id"] != c["id"] and tgt["id"] not in seen:
            seen.add(tgt["id"])
            items.append({"id": tgt["id"], "label": r["label"]})
    if not items:
        return
    with st.container(key=f"{uid}_seealso"):
        with st.expander(f"See also · {len(items)}", expanded=False):
            st.caption("Often discussed together in the textbooks; navigation only, not a clinical link.")
            concept_chips(items, f"{uid}_sa", lambda x: x["label"])


def _evidence_text(sid: str) -> str:
    book, _, rest = sid.partition("/")
    rest = re.sub(r"^(\d+-)+", "", rest).replace("-", " ").strip()
    return f"{BOOKS.get(book, book)} · {rest[:1].upper() + rest[1:]}" if rest else BOOKS.get(book, book)


def render_hub_page(hid: str) -> bool:
    """A hub page: its members, paginated, each opening a concept page. Navigation only; no facts are shown here."""
    rows = _safe(lambda: _h_members(hid), [])
    if not rows:
        return False
    first = rows[0]
    t3 = first["tier"] == "T3"
    st.markdown('<div class="mm-trail">' + " › ".join(
        ["Explore"] + [esc((_safe(lambda t=t: _c_page(t), {}) or {}).get("label", "?"))
                       for t in ((st.session_state.get("ex_trail") or [])[-2:]
                                 + ([st.session_state["ex_cur"]] if st.session_state.get("ex_cur") else []))]
        + [f"<b>{esc(first['hub_label'])}</b>"]) + "</div>", unsafe_allow_html=True)
    b1, b2, _ = st.columns([1, 1.6, 3])
    b1.button("← Back", key="ex_hub_back", on_click=lambda: st.session_state.update(ex_hub=None), use_container_width=True)
    if _safe(lambda: _c_page(hid), {}):                  # class hubs are concepts too: offer their own page
        b2.button("Open concept page", key="ex_hub_open", on_click=_go, args=(hid,), use_container_width=True)
    st.markdown(f"### {esc(first['hub_label'])}", unsafe_allow_html=True)
    st.markdown(f'<div class="mm-pills"><span class="mm-pill info">{esc(HUB_KIND.get(first["hub_type"], "Group"))}</span>'
                f'<span class="mm-pill info">{len(rows)} members</span>{SUG_TAG if t3 else ""}</div>', unsafe_allow_html=True)
    st.caption("A group for browsing. Members share a heading, not their facts: treatments, cautions and other facts "
               "belong to each concept's own page." + (" " + SUGGESTED_TIP if t3 else ""))
    pages = max(1, -(-len(rows) // HUB_PAGE))
    pg = min(max(int(st.session_state.get("ex_hub_page", 0)), 0), pages - 1)
    st.session_state["ex_hub_page"] = pg
    chunk = rows[pg * HUB_PAGE:(pg + 1) * HUB_PAGE]
    concept_chips([{"id": r["member_id"], **r} for r in chunk], f"ex_hubm_{pg}", lambda r: r["member_label"])
    if pages > 1:
        p1, p2, p3 = st.columns([1, 1, 3])
        p1.button("← Prev", key="ex_hub_prev", disabled=pg == 0, use_container_width=True,
                  on_click=lambda: st.session_state.update(ex_hub_page=pg - 1))
        p2.button("Next →", key="ex_hub_next", disabled=pg >= pages - 1, use_container_width=True,
                  on_click=lambda: st.session_state.update(ex_hub_page=pg + 1))
        p3.caption(f"Page {pg + 1} of {pages} · members {pg * HUB_PAGE + 1}-{pg * HUB_PAGE + len(chunk)}")
    ev = [r for r in chunk if r.get("evidence")]
    if ev:
        with st.expander("Textbook section each grouping was checked against"):
            for r in ev:
                st.markdown(f'<div class="mm-hubpg"><b>{esc(r["member_label"])}</b> · {esc(_evidence_text(r["evidence"]))}</div>',
                            unsafe_allow_html=True)
    return True


def panel_graph(c: dict, uid: str) -> None:
    deep = st.toggle("Include neighbours of neighbours (2 hops, up to 40 concepts)", key=f"{uid}_hops")
    has_hubs = any(h["tier"] == "T2" for h in _safe(lambda: _h_for(c["label"]), []))
    show_hubs = st.toggle("Show hubs", key=f"{uid}_hubs", help="Add the groups this concept belongs to (organ system, "
                          "mechanism, organism genus) as square boxes on dotted lines.") if has_hubs else False
    dot, n, nh = _local_dot(c["id"], 2 if deep else 1, show_hubs)
    if n < 2 and not nh:
        return
    st.markdown('<div class="mm-label">Local graph</div>', unsafe_allow_html=True)
    st.graphviz_chart(dot, width="stretch")
    legend = "".join(f'<span class="mm-pill" style="background:{TYPE_FILL[t]};color:#15232a">{TYPE_NAME[t]}</span>'
                     for t in TYPE_FILL if t != "OrganSystem")
    if nh:
        legend += '<span class="mm-pill info"><span class="mm-hubnode"></span>Hub (group)</span>'
    st.markdown(f'<div class="mm-pills">{legend}</div>', unsafe_allow_html=True)
    st.caption(f"{n} concepts shown (most connected first, capped). Solid line: a certified fact stated from the "
               "arrow's start. Dashed line: the same fact read backwards (derived). Book mentions are not drawn here."
               + (" Dotted line to a square box: the concept is listed under that group." if nh else ""))


def render_concept_panels(c: dict, uid: str) -> None:
    """The navigation panels; each one is hidden when its data is missing or its call fails."""
    for fn in (lambda: panel_part_of(c, uid), lambda: panel_bodhi(c, uid), lambda: panel_links(c, uid),
               lambda: panel_related(c, uid), lambda: panel_mentions(c), lambda: panel_see_also(c, uid),
               lambda: panel_graph(c, uid)):
        try:
            fn()
        except Exception:
            pass


def render_facets(prof: dict) -> None:
    """Clinical facet tabs of one condition (certified facts, each with its source)."""
    panels = []   # (tab title, render function)
    if prof["presentation"]:
        panels.append(("Presentation", lambda: fact_list(prof["presentation"], "ex_pr")))
    if prof["etiology"] or prof["mechanism"]:
        def _em():
            for title, key in (("Etiology", "etiology"), ("Mechanism", "mechanism")):
                if prof[key]:
                    st.markdown(f"**{title}**")
                    fact_list(prof[key], f"ex_{key[:2]}")
        panels.append(("Etiology & mechanism", _em))
    if prof["diagnostics"]:
        panels.append(("Diagnostics", lambda: fact_list(prof["diagnostics"], "ex_dx")))
    if prof["therapy"]:
        def _th():
            for line, items in prof["therapy"].items():
                st.markdown(f"**{line}** · {', '.join(f['object_label'] for f in items)}")
                fact_list(items, f"ex_th_{line}")
        panels.append(("Stepwise therapy", _th))
    if prof["warnings"]:
        panels.append(("Warnings", lambda: fact_list(prof["warnings"], "ex_wa")))
    if any(prof[k] for k in ("differentials", "is_a", "drug_effects", "drug_mechanisms")):
        def _rel():
            for title, key, arrow in (("Differentials", "differentials", False), ("Is a", "is_a", False),
                                      ("Drug → adverse effect", "drug_effects", True),
                                      ("Drug → target", "drug_mechanisms", True)):
                if prof[key]:
                    st.markdown(f"**{title}**")
                    fact_list(prof[key], f"ex_{key[:3]}", arrow)
        panels.append(("Related", _rel))

    if not panels:
        st.info("No certified facts yet for this condition.")
    else:
        for tab, (_, render) in zip(st.tabs([t for t, _ in panels]), panels):
            with tab:
                render()


def render_atlas_links(label: str, ctype: str, key: str) -> None:
    """'View in 3D' for an anatomical structure, or for the structures a condition involves (certified
    INVOLVES_STRUCTURE facts). Navigation only. Hidden when ATLAS_URL is unset or nothing links. The atlas loads
    (33 MB of models) only after a click on the link, or after the inline toggle is switched on."""
    if not config.ATLAS_URL:
        return
    if ctype in ("AnatomicalStructure", "OrganSystem"):
        u = _safe(lambda: atlas.atlas_link(label))
        found = [{"label": label, "url": u}] if u else []
        btn = "View in 3D"
    elif ctype == "PathologicalCondition":
        found = _safe(lambda: atlas.structures_for(label), []) or []
        btn = "View involved structures in 3D"
    else:
        return
    if not found:
        return
    st.link_button(f"🧍 {btn}", found[0]["url"], help="Opens the 3D anatomy atlas in a new tab.")
    if len(found) > 1:
        st.caption("Also in 3D: " + " · ".join(f"[{esc(f['label'])}]({f['url']})" for f in found[1:]))
    with st.expander("Show the 3D view here", expanded=False):
        if st.toggle("Load the 3D view (about 33 MB)", key=f"atl_{key}"):
            st.components.v1.iframe(found[0]["url"], height=560)
        st.caption("Anatomy: BodyParts3D © DBCLS, CC BY 4.0, shown with the open-source Human Atlas viewer (MIT). "
                   "A navigation aid: it shows where a structure is, not a clinical finding.")


def render_concept_page(cid: str) -> bool:
    """A concept page for any entity type. Returns False (nothing drawn) when the concept cannot be loaded."""
    c = _safe(lambda: _c_page(cid), {})
    if not c:
        return False
    trail = [t for t in (st.session_state.get("ex_trail") or [])]
    names = [(_safe(lambda t=t: _c_page(t), {}) or {}).get("label", "?") for t in trail[-3:]]
    st.markdown('<div class="mm-trail">' + " › ".join(["Explore"] + [esc(n) for n in names] + [f"<b>{esc(c['label'])}</b>"])
                + "</div>", unsafe_allow_html=True)
    b1, b2, _ = st.columns([1, 1.4, 3])
    b1.button("← Back", key="ex_back", on_click=_back, use_container_width=True, disabled=not trail)
    b2.button("Browse by organ system", key="ex_home", on_click=_home, use_container_width=True)
    pills = f'<span class="mm-pill info">{esc(_type_name(c["type"]))}</span>'
    pills += "".join(f'<span class="mm-pill info">{esc(BOOKS.get(b, b))}</span>' for b in c.get("books", []))
    st.markdown(f"### {esc(c['label'])}", unsafe_allow_html=True)
    st.markdown(f'<div class="mm-pills">{pills}</div>', unsafe_allow_html=True)
    if c.get("aliases"):
        st.caption("Also written as: " + "; ".join(c["aliases"][:6]))
    same = c.get("same_label") or []
    if same:
        st.caption("The same name also appears as: " + ", ".join(sorted({_type_name(s["type"]) for s in same}))
                   + ". Shown separately, not merged.")
    if c["type"] == "PathologicalCondition":
        prof = _safe(lambda: onto.profile(c["label"]))
        if prof and prof.get("n_facts"):
            with st.expander("Certified facts for this condition, with sources", expanded=False):
                render_facets(prof)
    render_atlas_links(c["label"], c["type"], "cp_" + re.sub(r"\W+", "_", cid)[-40:])
    render_concept_panels(c, "cp_" + re.sub(r"\W+", "_", cid)[-40:])
    return True


with tab_explore:
    if not onto.available():
        st.info("The certified clinical ontology file (data/ontology/clinical_ontology.jsonl) is missing, so there "
                "is nothing to explore yet. Build it with the ontology pipeline and reload this page.")
    else:
        cat = onto.catalog()
        n_cond = sum(len(c) for s in cat.values() for c in s.values())
        st.markdown("### Explore certified clinical facts")
        st.markdown(f"Facts extracted by a language model from {onto_sections():,} textbook sections. Each fact's quote "
                    "was found word-for-word in its source, which proves the source says it, not that the fact was "
                    "read correctly. Open *Source* under any fact to check. Search any concept, or drill down from "
                    "organ system to a single condition.")
        st.markdown(f'<div class="mm-chips"><span class="mm-chip">{n_cond} conditions</span>'
                    f'<span class="mm-chip">{len(onto.facts()):,} certified facts</span></div>', unsafe_allow_html=True)
        st.write("")
        render_concept_search()
        st.write("")

        cur = st.session_state.get("ex_cur")
        hub = st.session_state.get("ex_hub")
        if hub and _safe(lambda: render_hub_page(hub), False):
            pass
        elif cur and render_concept_page(cur):
            st.session_state["ex_hub"] = None
        else:
            if cur:                                      # stale or unreadable concept: fall back to browsing
                _home()
            st.markdown('<div class="mm-label">1 · Organ system</div>', unsafe_allow_html=True)
            systems = list(cat)
            system = st.pills("Organ system", systems, selection_mode="single", default=systems[0],
                              key="ex_system", label_visibility="collapsed") or systems[0]

            cats = list(cat[system])
            st.markdown('<div class="mm-label">2 · Disease category</div>', unsafe_allow_html=True)
            category = st.pills("Disease category", cats, selection_mode="single", default=cats[0],
                                key=f"ex_cat_{system}", label_visibility="collapsed") or cats[0]

            conds = sorted(cat[system][category].items(), key=lambda kv: (-kv[1], kv[0]))
            counts = dict(conds)
            st.markdown('<div class="mm-label">3 · Condition</div>', unsafe_allow_html=True)
            cond = st.selectbox("Condition", [c for c, _ in conds], key=f"ex_cond_{system}_{category}",
                                format_func=lambda c: f"{c} · {counts[c]} facts", label_visibility="collapsed")
            prof = onto.profile(cond)
            render_atlas_links(cond, "PathologicalCondition", "dd_" + re.sub(r"\W+", "_", cond.lower())[:40])
            with st.expander("🕸️  Clinical graph for this condition", expanded=False):
                render_clinical_graph([], [cond], key="cg_ex_" + re.sub(r"\W+", "_", cond.lower())[:48])
            try:
                differ = onto.contradictions_for(cond)
            except Exception:
                differ = []
            if differ:
                books_differ(differ)
            if prof["stages"]:
                st.markdown('<div class="mm-label">Stages</div>' + "".join(
                    f'<span class="mm-pill info">{esc(f["object_label"])}</span>' for f in prof["stages"]),
                    unsafe_allow_html=True)

            st.markdown('<div class="mm-label" style="margin-top:.6rem">4 · Clinical facets</div>', unsafe_allow_html=True)
            render_facets(prof)

            cc = _safe(lambda: _c_page(cond), {}) if _concepts else {}
            if cc:
                st.markdown("---")
                st.markdown("#### Explore connections")
                render_concept_panels(cc, "dd_" + re.sub(r"\W+", "_", cond.lower())[:40])
