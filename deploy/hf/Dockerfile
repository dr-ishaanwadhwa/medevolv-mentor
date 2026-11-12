FROM python:3.13-slim

RUN useradd -m -u 1000 user
WORKDIR /app

# CPU-only torch first, so sentence-transformers does not pull the multi-GB CUDA build
COPY requirements.txt .
RUN pip install --no-cache-dir torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .
USER user
ENV HOME=/home/user HF_HOME=/home/user/.cache/huggingface \
    EMBED_BACKEND=local LLM_BACKEND=deepseek PYTHONUNBUFFERED=1

# Bake the embedding model into the image so the first question is not slow
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

EXPOSE 7860
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0", "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
