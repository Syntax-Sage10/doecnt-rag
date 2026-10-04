"""Guardrails: prompt-injection screening, prompt-safe sanitization, citation checks."""
import re

# Heuristic patterns commonly seen in indirect prompt-injection payloads.
# This is a cheap first filter, NOT a complete defense (see structural defenses in rag.py).
_INJECTION_PATTERNS = [
    r"ignore (all |any |the )?(previous|prior|above|earlier) (instructions|prompts|rules)",
    r"disregard (all |any |the )?(previous|prior|above|system)",
    r"forget (everything|all|your) (above|previous|instructions)",
    r"you are now (a|an|in)\b",
    r"new (system )?instructions?\s*:",
    r"(reveal|print|show|repeat) (your|the) (system )?(prompt|instructions)",
    r"\bsystem\s*prompt\b",
    r"act as (a|an|if)\b.{0,40}(unrestricted|jailbroken|dan)\b",
    r"do not (tell|inform) the user",
    r"(send|post|exfiltrate|upload).{0,40}(https?://|api key|password|secret)",
    r"!\[.*?\]\(https?://[^)]*\?[^)]*=",   # markdown-image exfil pattern
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE | re.DOTALL)

# Tags we use to delimit context; strip them from document text so a document
# cannot "close" the context block and smuggle in instructions.
_DELIMITER_RE = re.compile(
    r"</?\s*(chunk|context|system|instructions?|assistant|human|user)\b[^>]*>",
    re.IGNORECASE,
)
_CITATION_RE = re.compile(r"\[(\d+)\]")


def is_suspicious(text: str) -> bool:
    """True if the text matches known injection phrasing."""
    return bool(_INJECTION_RE.search(text))


def sanitize_for_prompt(text: str) -> str:
    """Neutralize delimiter tags and invisible control characters."""
    text = _DELIMITER_RE.sub("", text)
    # Remove zero-width / bidi control chars sometimes used to hide payloads.
    return re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]", "", text)


def extract_citations(answer: str) -> set[int]:
    return {int(n) for n in _CITATION_RE.findall(answer)}


def invalid_citations(answer: str, num_chunks: int) -> set[int]:
    """Citation numbers that don't correspond to any retrieved chunk."""
    return {n for n in extract_citations(answer) if not 1 <= n <= num_chunks}
