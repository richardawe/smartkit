"""
Extraction module — three tiers:
  Tier 0: Deterministic regex/keyword extraction (no LLM, no key required)
  Tier 1: OpenRouter free model (OPENROUTER_API_KEY set — Phase 2)
  Tier 2: Bring-your-own model/endpoint (user changes settings.yml — Phase 2)

The LLM ONLY converts free text into structured fields.
Keep/drop and ranking decisions live in score.py, never here.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_DATE_PATTERNS = [
    r'\b\d{4}-\d{2}-\d{2}\b',
    r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b',
    r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
]

_ACTION_KEYWORDS = {
    "enforcement": ["enforcement", "fine", "penalty", "sanction", "order", "violation",
                    "charged", "charges", "lawsuit", "sued"],
    "rulemaking":  ["proposed rule", "final rule", "rulemaking", "regulation", "amend",
                    "amendment", "notice of proposed"],
    "guidance":    ["guidance", "advisory", "notice", "bulletin", "faq", "frequently asked"],
    "settlement":  ["settlement", "consent order", "consent decree", "agree", "resolved",
                    "resolve"],
}


def _extract_dates(text: str) -> list[str]:
    dates = []
    for pattern in _DATE_PATTERNS:
        dates.extend(re.findall(pattern, text, re.IGNORECASE))
    seen = set()
    return [d for d in dates if not (d in seen or seen.add(d))]


def _extract_action_type(text: str) -> str:
    lower = text.lower()
    for action_type, keywords in _ACTION_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return action_type
    return "other"


def _extract_entities(text: str) -> list[str]:
    # Runs of two or more consecutive Title Case words (simple heuristic)
    candidates = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', text)
    seen: set[str] = set()
    return [c for c in candidates if not (c in seen or seen.add(c))][:10]


def _extract_key_terms(text: str, known_keywords: list[str]) -> list[str]:
    lower = text.lower()
    return [kw for kw in known_keywords if kw.lower() in lower]


def _truncate_summary(text: str, max_chars: int = 250) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    last_period = cut.rfind(".")
    return cut[: last_period + 1] if last_period > 80 else cut


def extract_tier0(item: dict, known_keywords: Optional[list[str]] = None) -> dict:
    """Deterministic extraction — no LLM required."""
    raw = item.get("raw_text", "") or f"{item.get('title', '')} {item.get('summary', '')}"
    summary_src = item.get("summary", "") or item.get("title", "")

    return {
        **item,
        "extracted": {
            "topics": [],                                       # populated by LLM in Tier 1+
            "entities": _extract_entities(raw),
            "dates": _extract_dates(raw),
            "key_terms": _extract_key_terms(raw, known_keywords or []),
            "summary": _truncate_summary(summary_src),
            "action_type": _extract_action_type(raw),
            "extraction_tier": 0,
        },
    }


def extract_all(
    items: list[dict],
    settings: dict,
    known_keywords: Optional[list[str]] = None,
) -> list[dict]:
    """
    Extract structured fields from all items.
    Phase 1: Tier 0 only.
    # v2: Tier 1/2 (llm.py) logic will be inserted here — check for API key,
    #     call llm.py, validate JSON schema, fall back to Tier 0 on any error.
    """
    results = []
    for item in items:
        try:
            results.append(extract_tier0(item, known_keywords))
        except Exception as e:
            logger.warning(f"Extraction failed for '{item.get('title', '')}': {e}")
            results.append({
                **item,
                "extracted": {
                    "extraction_tier": 0,
                    "summary": item.get("summary", ""),
                    "action_type": "other",
                    "entities": [],
                    "dates": [],
                    "key_terms": [],
                    "topics": [],
                },
            })

    logger.info(f"Extracted {len(results)} items (Tier 0 — deterministic)")
    return results
