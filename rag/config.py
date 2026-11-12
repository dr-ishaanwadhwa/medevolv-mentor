"""All runtime settings, read from environment variables (put them in .env, which is git-ignored).

Backends are swappable so the team can develop before OCI is set up:
  EMBED_BACKEND = local | oci      local = sentence-transformers on this machine
  LLM_BACKEND   = ollama | oci | deepseek     ollama = a local model, also the offline demo backup
Changing EMBED_BACKEND needs a re-index (each backend gets its own Chroma collection).
"""
import os
from pathlib import Path


def _load_dotenv(path: Path = Path(".env")) -> None:
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()

EMBED_BACKEND = os.getenv("EMBED_BACKEND", "local")
LLM_BACKEND = os.getenv("LLM_BACKEND", "ollama")

LOCAL_EMBED_MODEL = os.getenv("LOCAL_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

# OCI Generative AI (needs ~/.oci/config from `oci setup config`, plus a compartment OCID)
OCI_CONFIG_PROFILE = os.getenv("OCI_CONFIG_PROFILE", "DEFAULT")
OCI_REGION = os.getenv("OCI_REGION", "us-chicago-1")
OCI_COMPARTMENT_ID = os.getenv("OCI_COMPARTMENT_ID", "")
OCI_EMBED_MODEL = os.getenv("OCI_EMBED_MODEL", "cohere.embed-english-v3.0")
OCI_CHAT_MODEL = os.getenv("OCI_CHAT_MODEL", "meta.llama-3.3-70b-instruct")

# DeepSeek (OpenAI-compatible). The key lives only in .env / the host's secret store, never in git or chat.
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Google Gemini (AI Studio key). Interactions API per aistudio.google.com/docs (2026-11): POST /v1beta/interactions,
# header x-goog-api-key, thinking via generation_config.thinking_level. Key lives only in .env / host secrets.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_THINKING = os.getenv("GEMINI_THINKING", "minimal")      # minimal | low | medium | high
GEMINI_URL = os.getenv("GEMINI_URL", "https://generativelanguage.googleapis.com/v1beta/interactions")

OKF_DIR = Path(os.getenv("OKF_DIR", "data/okf"))
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", "data/chroma"))

CHUNK_WORDS = int(os.getenv("CHUNK_WORDS", "300"))      # bge-small caps at 512 tokens ≈ 380 words
TOP_K = int(os.getenv("TOP_K", "6"))
# Below this cosine similarity the best hit is treated as "not in my sources". Calibrate with eval/.
# bge-small on Tripathi: on-topic queries scored 0.71–0.81, off-topic ~0.50 (2026-11-07 probe).
MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY", "0.60"))

# The ToC router and STAIR are kept in the repo but hidden from the demo UI (router scored 32% chapter@1 vs 77% for
# vector on the local 3B model; STAIR training is optional future work). EXPERIMENTAL=1 shows them again.
EXPERIMENTAL = os.getenv("EXPERIMENTAL", "0") == "1"
