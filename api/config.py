"""Central configuration. Everything can be overridden with environment variables or a .env file."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Chroma sends anonymous telemetry by default; keep it off.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

METRO_BIN = Path(os.getenv("METRO_BIN", ROOT / "build" / "metro"))
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
KNOWLEDGE_DIR = Path(os.getenv("KNOWLEDGE_DIR", ROOT / "knowledge"))
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", ROOT / ".chroma"))

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# Hard cap on agent steps (model call + tool call each count) so a confused agent cannot loop forever.
AGENT_RECURSION_LIMIT = int(os.getenv("AGENT_RECURSION_LIMIT", "12"))
# How many chunks each retrieval tool returns.
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "4"))
