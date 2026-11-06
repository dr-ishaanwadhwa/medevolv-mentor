"""Embedding and LLM backends behind two small functions: embed() and chat()."""
from __future__ import annotations

import functools
import json
import urllib.request

from rag import config

BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


# ---------- embeddings ----------
@functools.cache
def _local_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(config.LOCAL_EMBED_MODEL)


@functools.cache
def _oci_client():
    import oci
    cfg = oci.config.from_file(profile_name=config.OCI_CONFIG_PROFILE)
    endpoint = f"https://inference.generativeai.{config.OCI_REGION}.oci.oraclecloud.com"
    return oci.generative_ai_inference.GenerativeAiInferenceClient(cfg, service_endpoint=endpoint)


def embed(texts: list[str], is_query: bool = False) -> list[list[float]]:
    if config.EMBED_BACKEND == "local":
        if is_query and "bge" in config.LOCAL_EMBED_MODEL:
            texts = [BGE_QUERY_PREFIX + t for t in texts]
        return _local_model().encode(texts, normalize_embeddings=True, batch_size=32).tolist()

    if config.EMBED_BACKEND == "oci":
        from oci.generative_ai_inference import models as m
        out: list[list[float]] = []
        for i in range(0, len(texts), 96):  # OCI accepts up to 96 inputs per call
            details = m.EmbedTextDetails(
                inputs=texts[i:i + 96],
                serving_mode=m.OnDemandServingMode(model_id=config.OCI_EMBED_MODEL),
                compartment_id=config.OCI_COMPARTMENT_ID,
                input_type="SEARCH_QUERY" if is_query else "SEARCH_DOCUMENT",
                truncate="END",
            )
            out.extend(_oci_client().embed_text(details).data.embeddings)
        return out

    raise ValueError(f"Unknown EMBED_BACKEND={config.EMBED_BACKEND}")


# ---------- chat ----------
def chat(system: str, user: str, temperature: float = 0.1, max_tokens: int = 900, json_mode: bool = False) -> str:
    """json_mode asks the backend for a JSON object (Ollama enforces it; for OCI the prompt must ask for JSON)."""
    if config.LLM_BACKEND == "ollama":
        body = json.dumps({
            "model": config.OLLAMA_MODEL, "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            **({"format": "json"} if json_mode else {}),
        }).encode()
        req = urllib.request.Request(f"{config.OLLAMA_URL}/api/chat", body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.load(r)["message"]["content"]

    if config.LLM_BACKEND == "oci":
        from oci.generative_ai_inference import models as m
        req = m.GenericChatRequest(
            api_format="GENERIC",
            messages=[
                m.SystemMessage(content=[m.TextContent(text=system)]),
                m.UserMessage(content=[m.TextContent(text=user)]),
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        details = m.ChatDetails(
            compartment_id=config.OCI_COMPARTMENT_ID,
            serving_mode=m.OnDemandServingMode(model_id=config.OCI_CHAT_MODEL),
            chat_request=req,
        )
        resp = _oci_client().chat(details).data.chat_response
        return resp.choices[0].message.content[0].text

    raise ValueError(f"Unknown LLM_BACKEND={config.LLM_BACKEND}")
