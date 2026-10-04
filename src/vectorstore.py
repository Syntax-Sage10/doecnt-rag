"""Thin ChromaDB wrapper: embedding, upsert, similarity search, deletion."""
from __future__ import annotations

from dataclasses import dataclass

import chromadb
from chromadb.utils import embedding_functions

from .config import settings
from .ingestion import Chunk


@dataclass
class Retrieved:
    chunk_id: str
    text: str
    source: str
    page: int
    score: float          # cosine similarity in [0, 1]; higher = more relevant


class VectorStore:
    def __init__(self) -> None:
        self._client = chromadb.PersistentClient(path=settings.chroma_dir)
        self._embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.embedding_model
        )
        self._col = self._client.get_or_create_collection(
            name=settings.collection_name,
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},   # distance = 1 - cosine similarity
        )

    # ---- write ----
    def add_chunks(self, chunks: list[Chunk], batch_size: int = 64) -> None:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            self._col.upsert(
                ids=[c.id for c in batch],
                documents=[c.text for c in batch],
                metadatas=[c.metadata for c in batch],
            )

    def delete_source(self, source: str) -> None:
        self._col.delete(where={"source": source})

    # ---- read ----
    def search(
        self, query: str, k: int | None = None, sources: list[str] | None = None
    ) -> list[Retrieved]:
        if self._col.count() == 0:
            return []
        where = {"source": {"$in": sources}} if sources else None
        res = self._col.query(
            query_texts=[query],
            n_results=k or settings.top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        out = []
        for cid, doc, meta, dist in zip(
            res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0]
        ):
            out.append(
                Retrieved(
                    chunk_id=cid,
                    text=doc,
                    source=meta["source"],
                    page=int(meta.get("page", 0)),
                    score=max(0.0, 1.0 - float(dist)),
                )
            )
        return out

    def list_sources(self) -> dict[str, int]:
        """{filename: chunk_count}"""
        metas = self._col.get(include=["metadatas"])["metadatas"]
        counts: dict[str, int] = {}
        for m in metas:
            counts[m["source"]] = counts.get(m["source"], 0) + 1
        return dict(sorted(counts.items()))

    def count(self) -> int:
        return self._col.count()
