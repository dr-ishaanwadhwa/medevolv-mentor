"""MedEvolv Mentor: Streamlit UI.  Run:  .venv/bin/streamlit run app.py

Two tabs:
  Ask           chat; every answer carries its sources and a step-by-step record of how it was made
  How it works  the pipeline explained for a first-time viewer (diagram, stages, safety rules, evaluation)
"""
import hmac
import html
import os
import re

import streamlit as st

from rag import config, trace
from rag.answer import answer, answer_multihop
from rag.trace import STAGES

st.set_page_config(page_title="MedEvolv Mentor", page_icon="🩺", layout="wide",
                   initial_sidebar_state="collapsed")

# ---------------------------------------------------------------- style
st.html("""
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root { --ink:#15232a; --muted:#5a6b72; --line:#d7e0e2; --accent:#0f6b74; --accent-soft:#e2f0f1;
        --good:#1d7a46; --good-soft:#e3f3ea; --warn:#9a6200; --warn-soft:#fbf0db; --bad:#b0323a; --bad-soft:#f8e3e4;
        --card:#ffffff; --mono:"IBM Plex Mono", ui-monospace, Menlo, monospace; }
.stApp, .stApp p, .stApp li, .stApp button, .stApp input, .stApp textarea, .stApp label { font-family: "Instrument Sans", system-ui, sans-serif; }
/* never override Streamlit's icon font, or icon names render as text */
[data-testid="stIconMaterial"], [class*="material-symbols"], [class*="MaterialSymbols"] { font-family: "Material Symbols Rounded" !important; }
/* demo-question buttons: show the whole question */
.stButton button { height: auto; min-height: 2.6rem; padding: .45rem .8rem; text-align: left; justify-content: flex-start; }
.stButton button p, .stButton button div { white-space: normal !important; overflow: visible !important; text-overflow: clip !important; text-align: left; line-height: 1.35; }
.block-container { padding-top: 1.6rem; max-width: 1100px; }
h1, h2, h3 { letter-spacing: -0.01em; }

.mm-hero { display:grid; gap:.55rem; padding: .4rem 0 1.1rem; border-bottom:1px solid var(--line); margin-bottom: .4rem; }
.mm-eyebrow { font: 500 .74rem var(--mono); letter-spacing:.09em; text-transform:uppercase; color:var(--accent); }
.mm-title { font-size: 2.3rem; font-weight: 700; line-height:1.1; color:var(--ink); margin:0; }
.mm-sub { color:var(--muted); font-size:1.05rem; max-width: 70ch; margin:0; }
.mm-chips { display:flex; flex-wrap:wrap; gap:.4rem; margin-top:.25rem; }
.mm-chip { font: 500 .78rem var(--mono); background: var(--accent-soft); color: var(--accent);
           padding: .18rem .6rem; border-radius: 999px; }

.mm-label { font: 500 .72rem var(--mono); letter-spacing:.07em; text-transform:uppercase; color:var(--muted); }
.mm-pill { display:inline-block; font:500 .74rem var(--mono); padding:.15rem .6rem; border-radius:999px; margin-right:.35rem; }
.mm-pill.good { background:var(--good-soft); color:var(--good); }
.mm-pill.warn { background:var(--warn-soft); color:var(--warn); }
.mm-pill.bad  { background:var(--bad-soft);  color:var(--bad); }
.mm-pill.info { background:var(--accent-soft); color:var(--accent); }

/* step-by-step process timeline */
.mm-tl { list-style:none; margin:.2rem 0 0; padding:0; display:grid; gap:0; }
.mm-step { display:grid; grid-template-columns: 2.1rem 1fr auto; gap:.2rem .75rem; position:relative; padding:.55rem 0; }
.mm-step:not(:last-child)::before { content:""; position:absolute; left:1.02rem; top:2.3rem; bottom:-.4rem; width:2px; background:var(--line); }
.mm-dot { width:2.1rem; height:2.1rem; border-radius:50%; display:grid; place-items:center; font-size:1rem;
          background:var(--accent-soft); border:2px solid #fff; box-shadow:0 0 0 1px var(--line); z-index:1; }
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
.mm-src.cited { border-color: var(--accent); }
.mm-src-head { display:flex; flex-wrap:wrap; gap:.4rem; align-items:center; }
.mm-src-n { font: 600 .8rem var(--mono); color:var(--accent); }
.mm-src-where { font-size:.88rem; color:var(--ink); font-weight:500; }
.mm-src-ex { font-size:.84rem; color:var(--muted); line-height:1.45; }

/* how-it-works cards */
.mm-card { border:1px solid var(--line); border-radius:12px; background:var(--card); padding:1rem 1.05rem; height:100%; display:grid; gap:.35rem; align-content:start; }
.mm-card h4 { margin:0; font-size:1.02rem; }
.mm-card p { margin:0; color:var(--muted); font-size:.92rem; line-height:1.5; }
.mm-num { font: 600 .74rem var(--mono); color:var(--accent); }
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
ROUTE = {"graph": "Clinical case · graph route", "decompose": "Compound · split into parts",
         "single": "Single question · direct search"}
BOOKS = {"tripathi": "KD Tripathi · Pharmacology", "guyton": "Guyton & Hall · Physiology",
         "robbins": "Robbins · Pathology", "davidson": "Davidson · Medicine", "micro": "Microbiology",
         "harrison": "Harrison · Internal Medicine"}

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
  <p class="mm-sub">Ask exam questions or clinical cases. Every answer is built only from six standard textbooks
  and an open clinical knowledge graph, cites its sources, and shows exactly how it was made.</p>
  <div class="mm-chips">
    <span class="mm-chip">6 textbooks</span><span class="mm-chip">2,062 sections</span>
    <span class="mm-chip">33,830 passages</span><span class="mm-chip">6,560-node clinical graph</span>
    <span class="mm-chip">cites every claim</span><span class="mm-chip">declines when unsure</span>
  </div>
</div>
""")

tab_ask, tab_how = st.tabs(["💬  Ask", "🔍  How it works"])


# ---------------------------------------------------------------- rendering helpers
def esc(s) -> str:
    return html.escape(str(s))


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
        st.markdown('<div class="mm-label">Graph facts · Eka Care BODHI (CC BY-NC 4.0)</div>', unsafe_allow_html=True)
        for j, f in enumerate(p.graph_facts, 1):
            mark = " ✅" if j in res.graph_cited else ""
            st.markdown(f"**[G{j}]** {f}{mark}")
        st.markdown('<div class="mm-label" style="margin-top:.6rem">Textbook passages</div>', unsafe_allow_html=True)
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


def render_answer(res, steps, total_ms) -> None:
    label, tone = STATUS[res.status]
    route = ROUTE.get(res.plan.route) if res.plan is not None else None
    pills = f'<span class="mm-pill {tone}">{label}</span>'
    if route:
        pills += f'<span class="mm-pill info">{route}</span>'
    st.markdown(pills, unsafe_allow_html=True)
    st.markdown(res.text)
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

    for m in st.session_state.messages:
        with st.chat_message(m["role"], avatar="🧑‍⚕️" if m["role"] == "user" else "🩺"):
            if m["role"] == "user":
                st.markdown(m["content"])
            else:
                render_answer(m["result"], m["steps"], m["ms"])

    question = st.chat_input("Ask a medicine, pharmacology, pathology, physiology or microbiology question…")
    question = question or st.session_state.pop("pending", None)
    if question:
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
            render_answer(res, tr.steps, total)
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
  pdf [label="6 textbook\\nPDFs"]; toc [label="Recover contents\\n2,062 sections"];
  chunk [label="~250-word passages\\n33,830"]; emb [label="Embed\\n(bge-small)"];
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
        ("4", "📖 Textbook search", "The question (or each part) is turned into a vector and compared with all 33,830 "
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
                    "| Eka Care BODHI-S + BODHI-M (CC BY-NC 4.0) | Clinical graph | 6,560 nodes |")
    with right:
        st.markdown("#### How well it works")
        st.markdown("Tested on 36 questions covering every type (19 factual, 3 comparison, 5 clinical cases, "
                    "5 off-topic, 4 personal-advice), with multi-hop on:")
        st.markdown("| Measure | Result |\n|---|---|\n"
                    "| Right behaviour (answer / decline / refuse) | **36 / 36** |\n"
                    "| Cited passage from the right textbook | **22 / 22** |\n"
                    "| Answers with at least one citation | **27 / 27** |\n"
                    "| Correct chapter as top search result (446 questions) | **76.7%** |\n"
                    "| Correct chapter in top 3 | **91.0%** |\n"
                    "| Typical answer time | **~4 s** |")
        st.markdown("#### Known limits")
        st.markdown("- The graph is missing some classic symptom links (e.g. night sweats for TB), so a few "
                    "clinical cases get a weak differential; the trace shows this openly.\n"
                    "- Answers are only as complete as the five indexed books.\n"
                    "- A study aid for students, not clinical decision support.")
    st.markdown("#### Built with")
    st.markdown(" ".join(f'<span class="mm-chip">{t}</span>' for t in
                         ["Python", "Streamlit", "Chroma", "bge-small-en-v1.5", "DeepSeek", "networkx",
                          "PyMuPDF", "Oracle Cloud", "Caddy"]), unsafe_allow_html=True)
