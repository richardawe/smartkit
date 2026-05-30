"""
Extraction module — three tiers:
  Tier 0: Deterministic regex/keyword extraction (no LLM, no key required)
  Tier 1: OpenRouter free model (OPENROUTER_API_KEY set — default mode)
  Tier 2: Bring-your-own model/endpoint (user changes settings.yml)

The LLM ONLY converts free text into structured fields.
Keep/drop and ranking decisions live in score.py, never here.
"""
import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tier 0 — deterministic helpers
# ---------------------------------------------------------------------------

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
    seen: set[str] = set()
    return [d for d in dates if not (d in seen or seen.add(d))]


def _extract_action_type(text: str) -> str:
    lower = text.lower()
    for action_type, keywords in _ACTION_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return action_type
    return "other"


def _extract_entities(text: str) -> list[str]:
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
            "topics": [],
            "entities": _extract_entities(raw),
            "dates": _extract_dates(raw),
            "key_terms": _extract_key_terms(raw, known_keywords or []),
            "summary": _truncate_summary(summary_src),
            "action_type": _extract_action_type(raw),
            "extraction_tier": 0,
        },
    }


# ---------------------------------------------------------------------------
# Tier 1/2 — LLM-assisted extraction
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS = {"topics", "entities", "dates", "key_terms", "summary", "action_type"}
_VALID_ACTION_TYPES = {"enforcement", "rulemaking", "guidance", "settlement", "other"}
_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "extract.md"
_MAX_TEXT_CHARS = 2000  # cap sent to the LLM to stay within token budget


def _build_prompt(raw_text: str) -> str:
    template = _PROMPT_PATH.read_text()
    return template.replace("{text}", raw_text[:_MAX_TEXT_CHARS])


def _validate_llm_response(data: dict) -> dict:
    """Raise ValueError if required fields are missing; normalise types."""
    missing = _REQUIRED_FIELDS - data.keys()
    if missing:
        raise ValueError(f"LLM response missing required fields: {missing}")

    action = str(data.get("action_type", "other")).lower()
    return {
        "topics":     [str(t) for t in (data.get("topics") or [])],
        "entities":   [str(e) for e in (data.get("entities") or [])],
        "dates":      [str(d) for d in (data.get("dates") or [])],
        "key_terms":  [str(k) for k in (data.get("key_terms") or [])],
        "summary":    str(data.get("summary", ""))[:300],
        "action_type": action if action in _VALID_ACTION_TYPES else "other",
        "extraction_tier": 1,
    }


def extract_tier1(item: dict, settings: dict) -> dict:
    """
    LLM-assisted extraction (Tier 1/2).
    Raises on any failure — the caller in extract_all() catches and falls back to Tier 0.
    """
    from llm import call_llm  # late import so Phase 1 stub doesn't affect imports

    raw = item.get("raw_text", "") or f"{item.get('title', '')} {item.get('summary', '')}"
    prompt = _build_prompt(raw)
    raw_response = call_llm(prompt, settings)

    # Strip markdown fences some models wrap around JSON
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned.strip())

    extracted = _validate_llm_response(json.loads(cleaned))
    return {**item, "extracted": extracted}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def extract_all(
    items: list[dict],
    settings: dict,
    known_keywords: Optional[list[str]] = None,
) -> list[dict]:
    """
    Extract structured fields from all items.
    Uses Tier 1/2 when OPENROUTER_API_KEY is set; falls back to Tier 0 per item
    on any LLM failure (missing key, bad key, rate-limit, bad model, malformed JSON).
    Never crashes.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    use_llm = bool(api_key)

    if use_llm:
        model = settings.get("model", {}).get("name", "?")
        logger.info(f"Extraction mode: Tier 1/2 (model={model})")
    else:
        logger.info("Extraction mode: Tier 0 — no OPENROUTER_API_KEY set, using deterministic fallback")

    results: list[dict] = []
    tier1_count = 0
    tier0_fallback = 0

    for item in items:
        if use_llm:
            try:
                results.append(extract_tier1(item, settings))
                tier1_count += 1
                continue
            except Exception as e:
                logger.warning(
                    f"LLM extraction failed for '{item.get('title', '')[:60]}': {e} "
                    "— falling back to Tier 0"
                )
                tier0_fallback += 1

        # Tier 0 path (either no key, or LLM fallback)
        try:
            results.append(extract_tier0(item, known_keywords))
        except Exception as e:
            logger.warning(f"Tier 0 extraction error: {e}")
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

    if use_llm:
        logger.info(
            f"Extracted {len(results)} items: "
            f"{tier1_count} via LLM (Tier 1), {tier0_fallback} Tier 0 fallback"
        )
    else:
        logger.info(f"Extracted {len(results)} items (Tier 0 — deterministic)")

    return results
