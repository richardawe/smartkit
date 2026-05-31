import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def _serialize(item: dict) -> dict:
    ex = item.get("extracted", {})
    return {
        "title":          item.get("title", ""),
        "summary":        ex.get("summary", "") or item.get("summary", ""),
        "url":            item.get("url", ""),
        "published":      item.get("published", ""),
        "source":         item.get("source", ""),
        "score":          round(item.get("score", 0.0), 3),
        "action_type":    ex.get("action_type", "other"),
        "entities":       ex.get("entities", []),
        "dates":          ex.get("dates", []),
        "key_terms":      ex.get("key_terms", []),
        "extraction_tier": ex.get("extraction_tier", 0),
    }


def render(items: list[dict], settings: dict, output_path: str = "data/latest.json") -> None:
    """Write current items to data/latest.json and data/latest.js — current state only, never history."""
    dash = settings.get("dashboard", {})
    payload = {
        "generated_at":  datetime.now(timezone.utc).isoformat(),
        "title":         dash.get("title", "SmartKit Dashboard"),
        "subtitle":      dash.get("subtitle", ""),
        "schedule_note": dash.get("schedule_note", ""),
        "item_count":    len(items),
        "items":         [_serialize(i) for i in items],
    }
    json_str = json.dumps(payload, indent=2, ensure_ascii=False)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json_str)
    logger.info(f"Rendered {len(items)} items → {output_path}")

    # Write a JS-loadable copy so dashboard/index.html works with file://
    # (script tags work with file://; fetch() does not).
    js_out = out.with_suffix(".js")
    js_out.write_text(f"window.SMARTKIT_DATA = {json_str};\n")
    logger.info(f"Rendered {len(items)} items → {js_out}")
