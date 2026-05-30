import logging
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))

from fetch import fetch_all
from extract import extract_all
from score import score_and_filter
from render import render

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _load(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def main() -> None:
    logger.info("=== SmartKit pipeline starting ===")

    config_dir = PROJECT_ROOT / "config"
    sources  = _load(config_dir / "sources.yml").get("sources", [])
    rules    = _load(config_dir / "rules.yml")
    settings = _load(config_dir / "settings.yml")

    if not sources:
        logger.error("No sources configured in config/sources.yml — add at least one URL")
        sys.exit(1)

    logger.info(f"Loaded {len(sources)} source(s)")
    known_keywords = list(rules.get("keywords", {}).keys())

    items = fetch_all(sources)
    if not items:
        logger.warning("No items fetched — check sources and network connectivity")

    items = extract_all(items, settings, known_keywords)
    items = score_and_filter(items, rules)

    output_path = str(PROJECT_ROOT / "data" / "latest.json")
    render(items, settings, output_path)

    logger.info(f"=== Pipeline complete — {len(items)} items written to dashboard ===")


if __name__ == "__main__":
    main()
