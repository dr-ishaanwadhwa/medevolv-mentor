"""Embedding and LLM backends behind two small functions: embed() and chat()."""
from __future__ import annotations

import functools
import json
import time
import urllib.error
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
def chat(system: str, user: str, temperature: float = 0.1, max_tokens: int = 900, json_mode: bool = False,
         schema: dict | None = None, model: str | None = None) -> str:
    """json_mode asks for a JSON object; schema (a JSON Schema) constrains decoding on Ollama -- e.g. an enum of
    real ToC titles, so the model cannot output a title that does not exist. On OCI the caller must validate."""
    if config.LLM_BACKEND == "ollama" or model:          # a named local model (e.g. STAIR) always runs on Ollama
        body = json.dumps({
            "model": model or config.OLLAMA_MODEL, "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            **({"format": schema} if schema else ({"format": "json"} if json_mode else {})),
        }).encode()
        req = urllib.request.Request(f"{config.OLLAMA_URL}/api/chat", body, {"Content-Type": "application/json"})
        for attempt in range(3):                   # Ollama returns 500 / drops connections under contention
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    return json.load(r)["message"]["content"]
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    raise RuntimeError(f"Ollama has no model '{model or config.OLLAMA_MODEL}'. "
                                       f"Run: ollama pull {model or config.OLLAMA_MODEL}") from e
                err = e
            except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
                err = e
            time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"The local LLM (Ollama at {config.OLLAMA_URL}) is not responding: {err}. "
                           "Start the Ollama app and try again.") from err

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

    if config.LLM_BACKEND == "deepseek":
        return _deepseek_chat(system, user, temperature, max_tokens, json_mode or schema is not None)

    raise ValueError(f"Unknown LLM_BACKEND={config.LLM_BACKEND}")


def _deepseek_chat(system: str, user: str, temperature: float, max_tokens: int, json_mode: bool) -> str:
    """DeepSeek's OpenAI-compatible chat API. No enum-constrained decoding here: callers that need a fixed label set
    (the router) snap the reply to the nearest real title themselves."""
    if not config.DEEPSEEK_API_KEY:
        raise RuntimeError("LLM_BACKEND=deepseek but DEEPSEEK_API_KEY is not set (add it to .env or the host's secrets).")
    if json_mode:                                   # DeepSeek's JSON mode requires the word "json" in the prompt
        system += "\nReply with a single JSON object."
    body = json.dumps({
        "model": config.DEEPSEEK_MODEL, "temperature": temperature, "max_tokens": max_tokens, "stream": False,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        **({"response_format": {"type": "json_object"}} if json_mode else {}),
    }).encode()
    req = urllib.request.Request(f"{config.DEEPSEEK_BASE_URL}/chat/completions", body, {
        "Content-Type": "application/json", "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}"})
    err: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)["choices"][0]["message"]["content"] or ""
        except urllib.error.HTTPError as e:
            if e.code in (401, 402, 403):           # bad key / no balance: retrying will not help
                raise RuntimeError(f"DeepSeek API refused the request (HTTP {e.code}). Check the key and balance.") from e
            err = e                                 # 429 rate limit, 5xx overload
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            err = e
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"DeepSeek API is not responding: {err}") from err
