"""Embedding and LLM backends behind two small functions: embed() and chat()."""
from __future__ import annotations

import functools
import json
import time
import urllib.error
import urllib.request

from rag import config, trace

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
def model_name(model: str | None = None) -> str:
    if model:
        return model
    return {"deepseek": config.DEEPSEEK_MODEL, "ollama": config.OLLAMA_MODEL,
            "oci": config.OCI_CHAT_MODEL, "gemini": config.GEMINI_MODEL,
            "openrouter": config.OPENROUTER_MODEL, "mistral": config.MISTRAL_MODEL}.get(config.LLM_BACKEND, config.LLM_BACKEND)


def chat(system: str, user: str, temperature: float = 0.1, max_tokens: int = 900, json_mode: bool = False,
         schema: dict | None = None, model: str | None = None, purpose: str = "LLM call") -> str:
    with trace.timer() as t:
        out = _chat(system, user, temperature, max_tokens, json_mode, schema, model)
    n_in = len(system) + len(user)
    trace.record("llm", purpose, f"{config.LLM_BACKEND} · {model_name(model)}", ms=t.ms, model=model_name(model),
                 approx_tokens_in=n_in // 4, approx_tokens_out=len(out) // 4, temperature=temperature)
    return out


def _chat(system: str, user: str, temperature: float = 0.1, max_tokens: int = 900, json_mode: bool = False,
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

    if config.LLM_BACKEND == "gemini":
        return _gemini_chat(system, user, max_tokens, json_mode or schema is not None)

    if config.LLM_BACKEND == "openrouter":
        return _openrouter_chat(system, user, temperature, max_tokens, json_mode or schema is not None)

    if config.LLM_BACKEND == "mistral":
        return _mistral_chat(system, user, temperature, max_tokens, json_mode or schema is not None)

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


def _gemini_text(data: dict) -> str:
    """Generated text from an Interactions API response: the last 'model_output' step's text parts."""
    steps = data.get("steps") or []
    outputs = [st for st in steps if st.get("type") == "model_output"] or steps
    for step in reversed(outputs):
        parts = [c.get("text", "") for c in (step.get("content") or []) if isinstance(c, dict)]
        if any(parts):
            return "".join(parts)
    return data.get("output_text", "") or ""


def _gemini_chat(system: str, user: str, max_tokens: int, json_mode: bool) -> str:
    """Google Gemini via the Interactions API. Temperature is not sent: the docs say newer Gemini models ignore it
    and do not state that the default model accepts it."""
    if not config.GEMINI_API_KEY:
        raise RuntimeError("LLM_BACKEND=gemini but GEMINI_API_KEY is not set (add it to .env or the host's secrets).")
    body = {
        "model": config.GEMINI_MODEL,
        "system_instruction": system,
        "input": user,
        # thinking tokens count against max_output_tokens, so leave headroom above the answer budget
        "generation_config": {"max_output_tokens": max_tokens + 2048, "thinking_level": config.GEMINI_THINKING},
    }
    if json_mode:
        body["response_format"] = {"type": "text", "mime_type": "application/json"}
    req = urllib.request.Request(config.GEMINI_URL, json.dumps(body).encode(), {
        "Content-Type": "application/json", "x-goog-api-key": config.GEMINI_API_KEY, "Api-Revision": "2026-05-20"})
    err: Exception | None = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.load(r)
            text = _gemini_text(data)
            if not text.strip():
                raise RuntimeError(f"Gemini returned no text (status={data.get('status')!r})")
            return text
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403):            # bad request / key: retrying will not help
                detail = e.read().decode("utf-8", "replace")[:300]
                raise RuntimeError(f"Gemini API refused the request (HTTP {e.code}): {detail}") from e
            err = e                                   # 429 rate limit, 5xx overload
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            err = e
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Gemini API is not responding: {err}") from err


def _openrouter_chat(system: str, user: str, temperature: float, max_tokens: int, json_mode: bool) -> str:
    """OpenRouter chat completions (OpenAI-compatible). JSON mode is requested, and dropped automatically if the
    routed provider rejects it (free listings don't always support response_format)."""
    if not config.OPENROUTER_API_KEY:
        raise RuntimeError("LLM_BACKEND=openrouter but OPENROUTER_API_KEY is not set (add it to .env).")
    body = {
        "model": config.OPENROUTER_MODEL, "temperature": temperature,
        # reasoning tokens count against max_tokens: leave headroom so the answer isn't cut off
        "max_tokens": max_tokens + 4096,
        "reasoning": {"effort": config.OPENROUTER_REASONING},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {config.OPENROUTER_API_KEY}"}
    err: Exception | None = None
    for attempt in range(6):
        req = urllib.request.Request(config.OPENROUTER_URL, json.dumps(body).encode(), headers)
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                data = json.load(r)
            if "error" in data:
                raise RuntimeError(f"OpenRouter error: {str(data['error'])[:200]}")
            choice = (data.get("choices") or [{}])[0]
            text = (choice.get("message") or {}).get("content") or ""
            if not text.strip():
                raise RuntimeError(f"OpenRouter returned no text (finish_reason={choice.get('finish_reason')!r})")
            return text
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            if e.code == 400 and "response_format" in body:      # provider doesn't support JSON mode: retry without
                body.pop("response_format")
                continue
            if e.code in (400, 401, 402, 403):
                raise RuntimeError(f"OpenRouter refused the request (HTTP {e.code}): {detail}") from e
            err = RuntimeError(f"HTTP {e.code}: {detail}")        # 429 (20/min or daily cap), 5xx
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            err = e
        time.sleep(4 * (attempt + 1))
    raise RuntimeError(f"OpenRouter is not responding: {err}") from err


def _mistral_chat(system: str, user: str, temperature: float, max_tokens: int, json_mode: bool) -> str:
    """Mistral chat completions. JSON mode requires the prompt itself to ask for JSON (Mistral API reference), so a
    one-line reminder is added to the system prompt when json_mode is on."""
    if not config.MISTRAL_API_KEY:
        raise RuntimeError("LLM_BACKEND=mistral but MISTRAL_API_KEY is not set (add it to .env).")
    if json_mode:
        system += "\nReply with a single JSON object."
    body = {"model": config.MISTRAL_MODEL, "temperature": temperature, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    req = urllib.request.Request(config.MISTRAL_URL, json.dumps(body).encode(), {
        "Content-Type": "application/json", "Authorization": f"Bearer {config.MISTRAL_API_KEY}"})
    err: Exception | None = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.load(r)
            text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            if not text.strip():
                raise RuntimeError("Mistral returned no text")
            return text
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            if e.code in (400, 401, 402, 403, 422):   # bad request / key / no credit: retrying will not help
                raise RuntimeError(f"Mistral refused the request (HTTP {e.code}): {detail}") from e
            err = RuntimeError(f"HTTP {e.code}: {detail}")   # 429 rate limit, 5xx
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            err = e
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Mistral API is not responding: {err}") from err
