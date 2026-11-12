"""Streamlit chat UI.  Run:  .venv/bin/streamlit run app.py"""
import streamlit as st

from rag import config
from rag.answer import answer, answer_multihop

st.set_page_config(page_title="Eka Study Companion", page_icon="💊", layout="wide")

STATUS_LABEL = {
    "answered": ("Grounded answer", "green"),
    "not_in_sources": ("Not in sources", "orange"),
    "insufficient": ("Evidence insufficient", "orange"),
    "personal_refusal": ("Personal medical advice declined", "red"),
}

with st.sidebar:
    st.title("💊 Eka Study Companion")
    st.caption("Study aid for medical students. Answers come only from 5 indexed textbooks and the BODHI graph, with citations.")
    st.divider()
    st.markdown("**Pipeline**")
    st.code("OKF sections → ~250-word chunks\n→ embeddings → Chroma\n→ [BODHI hops | decomposition]\n→ retrieval per hop → LLM → cited answer",
            language=None)
    st.markdown(f"- Embeddings: `{config.EMBED_BACKEND}`\n- LLM: `{config.LLM_BACKEND}`\n"
                f"- Top-k: `{config.TOP_K}`\n- Refusal threshold: `{config.MIN_SIMILARITY}`")
    if config.EXPERIMENTAL:
        retriever = st.radio(
            "Retriever (experimental)", ["vector", "router", "stair"], horizontal=True,
            format_func={"vector": "Vector", "router": "ToC router", "stair": "STAIR"}.get,
            help="Vector = embedding search over all books · ToC router = LLM picks chapter/section from the table "
                 "of contents, then searches inside it · STAIR = fine-tuned model does that routing")
    else:
        retriever = "vector"
    multihop = st.toggle("Multi-hop (BODHI graph + query decomposition)", value=True, disabled=retriever != "vector",
                         help="Off = baseline single-retrieval RAG, for before/after comparison. "
                              "Multi-hop runs on vector retrieval.")
    st.divider()
    st.markdown("**Try:**")
    examples = [
        "A patient has high fever, headache and joint pain after a mosquito bite. Likely diagnosis and treatment?",
        "What is the drug of choice for absence seizures and why?",
        "Compare the mechanism of action of penicillins and aminoglycosides",
        "Who won the 2011 cricket world cup?",
        "My mother has TB, how much rifampicin should she take?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state.pending = ex
    if st.button("Clear chat", type="secondary"):
        st.session_state.messages = []

st.session_state.setdefault("messages", [])


def render_evidence(res) -> None:
    label, color = STATUS_LABEL[res.status]
    cols = st.columns([1, 3])
    with cols[0]:
        st.badge(label, color=color)
    if res.agreed_drugs:
        with cols[1]:
            st.badge("BODHI cross-check agrees: " + ", ".join(res.agreed_drugs[:3]), color="blue")

    p = res.plan
    if p is not None and p.route != "single":
        with st.expander(f"Reasoning path ({p.route} route, {len(p.hops)} hops)"):
            for i, h in enumerate(p.hops, 1):
                icon = {"graph": "🕸️", "retrieve": "📖", "decompose": "🧩"}[h.kind]
                st.markdown(f"{i}. {icon} **{h.kind}** · `{h.query}`  \n→ {h.result}")
            if p.graph_facts:
                st.markdown("**Graph facts** (Eka Care BODHI, CC BY-NC 4.0)")
                for j, f in enumerate(p.graph_facts, 1):
                    st.markdown(f"- **[G{j}]** {f}" + (" ✅" if j in res.graph_cited else ""))
    if not res.hits:
        return
    with st.expander(f"Evidence ({len(res.cited)} cited of {len(res.hits)} retrieved)"):
        for i, h in enumerate(res.hits, 1):
            star = "✅ cited" if i in res.cited else "retrieved"
            st.markdown(f"**[{i}]** {h.citation()} · similarity `{h.similarity:.2f}` · {star}")
            # Short excerpt only: the books are copyrighted, the citation tells the reader where to look.
            st.caption(h.passage[:300] + ("…" if len(h.passage) > 300 else ""))


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("result"):
            render_evidence(msg["result"])

question = st.chat_input("Ask a medicine, pharmacology, pathology, physiology or microbiology question…") or st.session_state.pop("pending", None)
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        try:
            with st.spinner("Retrieving and answering…"):
                if retriever != "vector":
                    res = answer(question, retriever=retriever)
                else:
                    res = answer_multihop(question) if multihop else answer(question)
        except RuntimeError as e:                 # LLM backend down, model missing, STAIR not installed
            st.warning(str(e))
            st.stop()
        except Exception as e:                    # never show a raw traceback in the demo
            st.error(f"Something went wrong while answering ({type(e).__name__}). Please try again.")
            st.stop()
        st.markdown(res.text)
        st.caption("multi-hop" if retriever == "vector" and multihop else f"single retrieval · {retriever}")
        render_evidence(res)
    st.session_state.messages.append({"role": "assistant", "content": res.text, "result": res})
