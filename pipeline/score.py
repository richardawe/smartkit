"""
# INVARIANT: The LLM never decides relevance.
# The LLM only converts free text into structured fields.
# Keep/drop and ranking decisions live entirely in this module,
# reading deterministic rules from config/rules.yml.
"""
import logging

logger = logging.getLogger(__name__)


def score_item(item: dict, rules: dict) -> float:
    """Score a single item from keyword weights and source trust multiplier."""
    keywords = rules.get("keywords", {})
    source_trust = rules.get("source_trust", {})

    text = " ".join(filter(None, [
        item.get("title", ""),
        item.get("summary", ""),
        item.get("raw_text", ""),
    ])).lower()

    kw_score = sum(
        float(weight) for keyword, weight in keywords.items()
        if keyword.lower() in text
    )

    source = item.get("source", "")
    trust = float(source_trust.get(source, source_trust.get("default", 1.0)))

    return kw_score * trust


def score_and_filter(items: list[dict], rules: dict) -> list[dict]:
    """Score all items, drop below threshold, return top N ranked by score."""
    scoring_cfg = rules.get("scoring", {})
    threshold = float(scoring_cfg.get("threshold", 0.1))
    max_items = int(scoring_cfg.get("max_items", 20))

    scored, dropped = [], 0

    for item in items:
        s = score_item(item, rules)
        if s >= threshold:
            scored.append({**item, "score": s})
        else:
            dropped += 1

    scored.sort(key=lambda x: x["score"], reverse=True)
    scored = scored[:max_items]

    logger.info(
        f"Scoring: {len(scored)} items kept, {dropped} dropped "
        f"(threshold={threshold}, max={max_items})"
    )
    return scored
