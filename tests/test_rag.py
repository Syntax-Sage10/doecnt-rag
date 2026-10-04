from src.rag import REFUSAL, RAGPipeline
from src.vectorstore import Retrieved


class FakeStore:
    def __init__(self, hits): self.hits = hits
    def search(self, q, k=None, sources=None): return self.hits


class ExplodingLLM:
    def complete(self, *a, **k): raise AssertionError("LLM must not be called")


class EchoLLM:
    def complete(self, system, messages, max_tokens=None):
        return "Paris is the capital [1]."


def test_refuses_without_llm_when_below_threshold():
    store = FakeStore([Retrieved("1", "irrelevant", "a.md", 0, 0.05)])
    r = RAGPipeline(store, ExplodingLLM()).answer("Capital of France?")
    assert r.answer == REFUSAL and not r.grounded


def test_returns_sources_and_citation_check():
    store = FakeStore([Retrieved("1", "Paris is the capital of France.", "a.md", 0, 0.8)])
    r = RAGPipeline(store, EchoLLM()).answer("Capital of France?")
    assert r.grounded and len(r.sources) == 1 and not r.warnings
