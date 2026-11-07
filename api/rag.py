"""RAG layer: builds and queries two ChromaDB collections.

- ``dmrc_info``: chunks of the markdown files in ``knowledge/`` (fares, cards, luggage, timings).
- ``stations``: one short document per station, generated from the same CSVs the router uses.
"""
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import CHROMA_DIR, KNOWLEDGE_DIR
from .network import load_stations, station_describe

DMRC_COLLECTION = "dmrc_info"
STATION_COLLECTION = "stations"

CHUNK_SIZE = 700
CHUNK_OVERLAP = 100


def knowledge_documents(knowledge_dir: Path = KNOWLEDGE_DIR) -> list[Document]:
    """Split each knowledge/*.md file on headings first, then paragraphs, keeping the filename as source."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
    )
    docs: list[Document] = []
    for path in sorted(Path(knowledge_dir).glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        docs.extend(
            splitter.create_documents([path.read_text(encoding="utf-8")], metadatas=[{"source": path.name}])
        )
    return docs


def station_documents() -> list[Document]:
    return [
        Document(page_content=station_describe(st), metadata={"source": "stations.csv", "station": st.name})
        for st in load_stations()
    ]


def get_store(collection: str, embeddings: Embeddings, persist_dir: Path = CHROMA_DIR) -> Chroma:
    return Chroma(
        collection_name=collection,
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )


def ingest(
    embeddings: Embeddings,
    persist_dir: Path = CHROMA_DIR,
    knowledge_dir: Path = KNOWLEDGE_DIR,
) -> dict[str, int]:
    """(Re)build both collections from scratch. Safe to run repeatedly."""
    counts = {}
    for name, docs in (
        (DMRC_COLLECTION, knowledge_documents(knowledge_dir)),
        (STATION_COLLECTION, station_documents()),
    ):
        store = get_store(name, embeddings, persist_dir)
        store.delete_collection()
        store = get_store(name, embeddings, persist_dir)
        if docs:
            store.add_documents(docs)
        counts[name] = len(docs)
    return counts


def search(store: Chroma, query: str, k: int) -> list[dict]:
    hits = store.similarity_search(query, k=k)
    return [{"source": d.metadata.get("source", "unknown"), "text": d.page_content} for d in hits]


def is_empty(store: Chroma) -> bool:
    return store._collection.count() == 0  # noqa: SLF001 (no public count API in langchain-chroma)
