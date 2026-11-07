from api import rag


def test_knowledge_docs_are_chunked_and_sourced():
    docs = rag.knowledge_documents()
    assert docs and all(d.metadata["source"].endswith(".md") for d in docs)
    assert not any(d.metadata["source"].lower() == "readme.md" for d in docs)
    assert all(len(d.page_content) <= rag.CHUNK_SIZE + 50 for d in docs)


def test_station_documents_cover_every_station():
    assert len(rag.station_documents()) == 250


def test_ingest_and_retrieve(tmp_path, fake_embeddings):
    counts = rag.ingest(fake_embeddings, tmp_path)
    assert counts[rag.STATION_COLLECTION] == 250 and counts[rag.DMRC_COLLECTION] > 0

    store = rag.get_store(rag.DMRC_COLLECTION, fake_embeddings, tmp_path)
    target = rag.knowledge_documents()[0].page_content
    # Fake embeddings hash the text, so the identical chunk must come back first.
    assert rag.search(store, target, k=3)[0]["text"] == target


def test_ingest_is_idempotent(tmp_path, fake_embeddings):
    first = rag.ingest(fake_embeddings, tmp_path)
    second = rag.ingest(fake_embeddings, tmp_path)
    assert first == second
    store = rag.get_store(rag.STATION_COLLECTION, fake_embeddings, tmp_path)
    assert store._collection.count() == 250
