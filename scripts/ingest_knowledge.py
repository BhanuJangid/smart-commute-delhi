"""Build the ChromaDB collections (DMRC knowledge + station documents) using the configured embeddings backend.

Usage: python scripts/ingest_knowledge.py
Requires a configured LLM provider (OpenAI by default or Ollama via LLM_PROVIDER=ollama).
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import rag  # noqa: E402
from api.config import CHROMA_DIR, LLM_PROVIDER, OLLAMA_BASE_URL, OLLAMA_EMBEDDING_MODEL, OPENAI_EMBEDDING_MODEL  # noqa: E402


def main() -> int:
    if LLM_PROVIDER == "ollama":
        from langchain_ollama import OllamaEmbeddings

        counts = rag.ingest(OllamaEmbeddings(model=OLLAMA_EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL))
    else:
        if not os.getenv("OPENAI_API_KEY"):
            print("OPENAI_API_KEY is not set. Copy .env.example to .env and add your key.", file=sys.stderr)
            return 1
        from langchain_openai import OpenAIEmbeddings

        counts = rag.ingest(OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL))

    for name, n in counts.items():
        print(f"{name}: {n} chunks")
    print(f"Stored in {CHROMA_DIR}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(503)
