"""Central configuration. Override via environment variables."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    # Storage / models
    chroma_dir: str = os.getenv("CHROMA_DIR", "./data/chroma")
    collection_name: str = "documents"
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    llm_model: str = os.getenv("LLM_MODEL", "gemini-3.5-flash")
    judge_model: str = os.getenv("JUDGE_MODEL", "gemini-3.5-flash")

    # Chunking: ~1000 chars ≈ 250 tokens. Small enough for precise retrieval,
    # large enough to keep a full idea; 15% overlap preserves boundary context.
    chunk_size: int = 1000
    chunk_overlap: int = 150
    min_chunk_chars: int = 40

    # Retrieval
    top_k: int = 5
    min_score: float = 0.30          # cosine similarity gate (tune on your corpus)

    # Conversation / limits
    max_history_turns: int = 4
    max_upload_mb: int = 20
    max_answer_tokens: int = 1024

    # Guardrails
    quarantine_suspicious_chunks: bool = True


settings = Settings()
