"""Download Eka Care's BODHI-S and BODHI-M graphs into data/bodhi/ (CC BY-NC 4.0, non-commercial).

Usage: python -m ingest.fetch_bodhi
"""
from huggingface_hub import hf_hub_download

REPOS = ["ekacare/BODHI-S", "ekacare/BODHI-M"]
FILES = ["README.md", "data/triples.jsonl", "data/nl_facts.jsonl"]

for repo in REPOS:
    name = repo.split("/")[1]
    for f in FILES:
        path = hf_hub_download(repo, f, repo_type="dataset", local_dir=f"data/bodhi/{name}")
        print(path)
