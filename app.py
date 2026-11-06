"""Streamlit chat UI.  Run:  .venv/bin/streamlit run app.py"""
import streamlit as st

from rag import config
from rag.answer import answer

st.set_page_config(page_title="Eka Study Companion", page_icon="💊", layout="wide")

STATUS_LABEL = {
    "answered": ("Grounded answer", "green"),
    "not_in_sources": ("Not in sources", "orange"),
    "insufficient": ("Evidence insufficient", "orange"),
    "personal_refusal": ("Personal medical advice declined", "red"),
}

with st.sidebar:
    st.title("💊 Eka Study Companion")
    st.caption("Pharmacology study aid for medical students. Answers come only from the textbook, with citations.")
    st.divider()
    st.markdown("**Pipeline**")
    st.code("OKF sections → ~250-word chunks\n→ embeddings → Chroma\n→ top-k retrieval → LLM → cited answer",
            language=None)
    st.markdown(f"- Embeddings: `{config.EMBED_BACKEND}`\n- LLM: `{config.LLM_BACKEND}`\n"
                f"- Top-k: `{config.TOP_K}`\n- Refusal threshold: `{config.MIN_SIMILARITY}`")
    st.divider()
    st.markdown("**Try:**")
    examples = [
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
    st.badge(label, color=color)
    if not res.hits:
        return
    with st.expander(f"Evidence ({len(res.cited)} cited of {len(res.hits)} retrieved)"):
        for i, h in enumerate(res.hits, 1):
            star = "✅ cited" if i in res.cited else "retrieved"
            st.markdown(f"**[{i}]** {h.citation()} · similarity `{h.similarity:.2f}` · {star}")
            st.caption(h.passage[:700] + ("…" if len(h.passage) > 700 else ""))


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("result"):
            render_evidence(msg["result"])

question = st.chat_input("Ask a pharmacology question…") or st.session_state.pop("pending", None)
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Retrieving and answering…"):
            res = answer(question)
        st.markdown(res.text)
        render_evidence(res)
    st.session_state.messages.append({"role": "assistant", "content": res.text, "result": res})
