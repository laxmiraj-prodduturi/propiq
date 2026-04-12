from __future__ import annotations

import logging

from ..config import settings
from ..schemas import RetrievedDocument, UserContext

logger = logging.getLogger(__name__)

# Module-level singletons — initialised lazily on first call to init_vector_store()
_collection = None
_indexed: bool = False


# ---------------------------------------------------------------------------
# ChromaDB + embedding helpers
# ---------------------------------------------------------------------------

def _get_collection():
    global _collection
    if _collection is not None:
        return _collection
    try:
        import chromadb
        client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        _collection = client.get_or_create_collection(
            name="property_documents",
            metadata={"hnsw:space": "cosine"},
        )
        return _collection
    except Exception as exc:
        logger.warning("ChromaDB unavailable: %s", exc)
        return None


def _embed(texts: list[str]) -> list[list[float]] | None:
    """Generate embeddings via OpenAI. Returns None when API key is absent or call fails."""
    if not settings.OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=texts,
        )
        return [item.embedding for item in response.data]
    except Exception as exc:
        logger.warning("Embedding call failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Initialisation — index all documents once at service startup
# ---------------------------------------------------------------------------

def init_vector_store() -> None:
    """Index all backend documents into ChromaDB. Safe to call multiple times."""
    global _indexed
    if _indexed:
        return
    _indexed = True  # set early to prevent retry loops on failure

    collection = _get_collection()
    if collection is None:
        return

    try:
        from ..backend_bridge import all_documents
        docs = all_documents()
        if not docs:
            logger.info("No documents found to index.")
            return

        texts: list[str] = []
        ids: list[str] = []
        metadatas: list[dict] = []

        for doc in docs:
            snippet = _document_snippet(
                doc.file_name or "",
                doc.document_type or "",
                doc.related_entity or "",
            )
            text = " ".join(filter(None, [
                doc.document_type,
                doc.file_name,
                doc.related_entity,
                snippet,
            ]))
            texts.append(text)
            ids.append(str(doc.id))
            metadatas.append({
                "tenant_id": str(doc.tenant_id or ""),
                "document_type": doc.document_type or "",
                "related_entity": doc.related_entity or "",
                "file_name": doc.file_name or "",
            })

        embeddings = _embed(texts)
        if embeddings:
            collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
            logger.info("Indexed %d documents into ChromaDB with OpenAI embeddings.", len(docs))
        else:
            # Store text without custom embeddings; ChromaDB will handle retrieval by text
            collection.upsert(ids=ids, documents=texts, metadatas=metadatas)
            logger.info("Indexed %d documents into ChromaDB (no embeddings — keyword mode).", len(docs))

    except Exception as exc:
        logger.warning("Document indexing failed: %s", exc)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve_documents(query: str, user: UserContext) -> list[RetrievedDocument]:
    """Semantic retrieval from ChromaDB, falling back to keyword search."""
    collection = _get_collection()
    if collection is not None and _indexed:
        try:
            where = {"tenant_id": user.tenant_id}
            embeddings = _embed([query])

            if embeddings:
                results = collection.query(
                    query_embeddings=embeddings,
                    n_results=3,
                    where=where,
                )
            else:
                results = collection.query(
                    query_texts=[query],
                    n_results=3,
                    where=where,
                )

            retrieved: list[RetrievedDocument] = []
            ids = results.get("ids", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            for i, doc_id in enumerate(ids):
                distance = distances[i] if distances else 1.0
                if distance > 0.8:
                    continue  # skip low-relevance results
                meta = metas[i] if metas else {}
                retrieved.append(RetrievedDocument(
                    document_id=doc_id,
                    title=meta.get("file_name", "Unknown Document"),
                    snippet=_document_snippet(
                        meta.get("file_name", ""),
                        meta.get("document_type", ""),
                        meta.get("related_entity", ""),
                    ),
                    metadata=meta,
                ))
            if retrieved:
                return retrieved
        except Exception as exc:
            logger.warning("Vector search failed, falling back to keyword search: %s", exc)

    return _keyword_search(query, user)


def _keyword_search(query: str, user: UserContext) -> list[RetrievedDocument]:
    from .data_access import search_documents
    return search_documents(query, user)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def format_citations(citations: list[str]) -> str:
    if not citations:
        return ""
    return "Sources: " + ", ".join(citations) + "."


def _document_snippet(file_name: str, document_type: str, related_entity: str) -> str:
    lowered = file_name.lower()
    if "pet" in lowered:
        return "Pets require written owner approval and compliance with the lease addendum before occupancy with animals."
    if "lease" in lowered:
        return "Recurring rent is due on the first of each month and standard residential occupancy terms apply through the lease end date."
    if "maintenance" in lowered or document_type == "policy":
        return "Urgent issues should be triaged quickly, documented clearly, and routed through an approval step before external dispatch."
    return f"{(document_type or 'Document').title()} document related to {related_entity or 'the residential portfolio'}."
