"""LLM-as-a-judge evaluation: context relevance + answer faithfulness.

Usage:  python -m src.evaluation eval/golden_set.jsonl
"""
from __future__ import annotations

import json
import re
import statistics
import sys

from .config import settings
from .llm import LLMClient
from .rag import REFUSAL, RAGPipeline
from .vectorstore import VectorStore

_RELEVANCE_PROMPT = """You are a strict evaluator. Given a QUESTION and a numbered list of \
retrieved PASSAGES, decide for each passage whether it contains information useful for answering \
the question. Respond with JSON only: {"relevant": [true, false, ...]} with one boolean per passage."""

_FAITHFULNESS_PROMPT = """You are a strict fact-checker. Given CONTEXT passages and an ANSWER:
1. Split the answer into atomic factual claims (ignore citation markers like [1]).
2. For each claim, decide if it is fully supported by the CONTEXT alone (not by world knowledge).
Respond with JSON only: {"claims": [{"claim": "...", "supported": true}, ...]}.
If the answer is an "I don't know" refusal, return {"claims": []}."""


def _json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    try:
        return json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        return {}


class Judge:
    def __init__(self) -> None:
        self.llm = LLMClient(model=settings.judge_model)

    def context_relevance(self, question: str, passages: list[str]) -> float:
        if not passages:
            return 0.0
        numbered = "\n\n".join(f"[{i}] {p}" for i, p in enumerate(passages, 1))
        out = self.llm.complete(
            _RELEVANCE_PROMPT,
            [{"role": "user", "content": f"QUESTION: {question}\n\nPASSAGES:\n{numbered}"}],
            max_tokens=200,
        )
        flags = _json(out).get("relevant", [])
        return sum(bool(f) for f in flags) / max(len(passages), 1)

    def faithfulness(self, answer: str, passages: list[str]) -> float | None:
        """Fraction of supported claims; None if answer is a refusal (not scoreable)."""
        if answer.startswith(REFUSAL[:25]) or not passages:
            return None
        context = "\n\n".join(f"[{i}] {p}" for i, p in enumerate(passages, 1))
        out = self.llm.complete(
            _FAITHFULNESS_PROMPT,
            [{"role": "user", "content": f"CONTEXT:\n{context}\n\nANSWER:\n{answer}"}],
            max_tokens=800,
        )
        claims = _json(out).get("claims", [])
        if not claims:
            return None
        return sum(bool(c.get("supported")) for c in claims) / len(claims)


def run(golden_path: str) -> None:
    pipeline = RAGPipeline(VectorStore())
    judge = Judge()
    rel_scores, faith_scores, refusals = [], [], 0

    with open(golden_path, encoding="utf-8") as f:
        items = [json.loads(line) for line in f if line.strip()]

    for item in items:
        q = item["question"]
        r = pipeline.answer(q)
        passages = [s.text for s in r.sources]
        # Judge relevance on everything retrieved, not just what passed the gate
        retrieved = [h.text for h in pipeline.store.search(r.standalone_question or q)]
        rel = judge.context_relevance(q, retrieved)
        faith = judge.faithfulness(r.answer, passages)
        rel_scores.append(rel)
        if faith is not None:
            faith_scores.append(faith)
        if not r.grounded:
            refusals += 1
        print(f"Q: {q}\n   relevance={rel:.2f} faithfulness={faith} grounded={r.grounded}")

    print("\n=== SUMMARY ===")
    print(f"Mean context relevance : {statistics.mean(rel_scores):.2f}")
    if faith_scores:
        print(f"Mean faithfulness      : {statistics.mean(faith_scores):.2f}")
    print(f"Refusal rate           : {refusals}/{len(items)}")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "eval/golden_set.jsonl")
