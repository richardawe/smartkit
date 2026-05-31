import logging
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(title: str, summary: str, url: str, published: str, raw_text: str, source: str) -> dict:
    return {
        "title": (title or "").strip(),
        "summary": (summary or "").strip(),
        "url": url or "",
        "published": published or _now_iso(),
        "raw_text": (raw_text or "").strip(),
        "source": source or "",
    }


_HEADERS = {"User-Agent": "SmartKit/1.0"}
_TIMEOUT = 15


def fetch_rss(url: str, source_name: str) -> list[dict]:
    logger.info(f"Fetching RSS: {source_name} ({url})")
    try:
        # Use requests for the HTTP fetch so we get timeout + consistent error handling;
        # feedparser is used only as a parser, not a fetcher.
        if url.startswith(("http://", "https://")):
            resp = requests.get(url, timeout=_TIMEOUT, headers=_HEADERS)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        else:
            feed = feedparser.parse(url)  # local file path for testing
        items = []
        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "") or entry.get("description", "")
            link = entry.get("link", "")
            published = ""
            if getattr(entry, "published_parsed", None):
                try:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
                except Exception:
                    published = entry.get("published", "")
            else:
                published = entry.get("published", "")
            raw_text = f"{title} {summary}"
            items.append(_normalize(title, summary, link, published, raw_text, source_name))
        logger.info(f"  → {len(items)} items from {source_name}")
        return items
    except Exception as e:
        logger.warning(f"Failed to fetch RSS {url}: {e}")
        return []


def fetch_json(url: str, source_name: str) -> list[dict]:
    logger.info(f"Fetching JSON: {source_name} ({url})")
    try:
        resp = requests.get(url, timeout=_TIMEOUT, headers=_HEADERS)
        resp.raise_for_status()
        data = resp.json()

        if isinstance(data, list):
            entries = data
        elif isinstance(data, dict):
            for key in ("items", "articles", "results", "data"):
                if key in data and isinstance(data[key], list):
                    entries = data[key]
                    break
            else:
                logger.warning(f"JSON {url}: unrecognised structure, skipping")
                return []
        else:
            return []

        items = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            title = entry.get("title", "") or entry.get("name", "")
            summary = (entry.get("summary", "") or entry.get("description", "")
                       or entry.get("content_text", "") or entry.get("abstract", ""))
            link = (entry.get("url", "") or entry.get("link", "")
                    or entry.get("html_url", "") or entry.get("id", ""))
            published = (entry.get("date_published", "") or entry.get("published", "")
                         or entry.get("publication_date", "") or entry.get("date", ""))
            raw_text = f"{title} {summary}"
            items.append(_normalize(title, summary, link, published, raw_text, source_name))

        logger.info(f"  → {len(items)} items from {source_name}")
        return items
    except Exception as e:
        logger.warning(f"Failed to fetch JSON {url}: {e}")
        return []


def fetch_html(url: str, source_name: str) -> list[dict]:
    logger.info(f"Fetching HTML: {source_name} ({url})")
    try:
        resp = requests.get(url, timeout=_TIMEOUT, headers=_HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        items = []
        candidates = soup.find_all("article") or soup.find_all(["h2", "h3"])

        for elem in candidates[:30]:
            title = elem.get_text(separator=" ", strip=True)[:200]
            link_tag = elem.find("a") or (elem.parent and elem.parent.find("a"))
            href = ""
            if link_tag:
                href = link_tag.get("href", "") or ""
                if href and not href.startswith("http"):
                    href = urljoin(url, href)
                if link_tag.get_text(strip=True):
                    title = link_tag.get_text(strip=True)[:200]

            summary = ""
            p = elem.find("p") if hasattr(elem, "find") else None
            if p and hasattr(p, "get_text"):
                summary = p.get_text(separator=" ", strip=True)[:500]

            if title:
                items.append(_normalize(title, summary, href, "", f"{title} {summary}", source_name))

        logger.info(f"  → {len(items)} items from {source_name}")
        return items
    except Exception as e:
        logger.warning(f"Failed to fetch HTML {url}: {e}")
        return []


def fetch_all(sources: list[dict]) -> list[dict]:
    all_items = []
    for source in sources:
        url = source.get("url", "")
        source_type = source.get("type", "rss").lower()
        name = source.get("name", url)

        if not url:
            logger.warning(f"Source missing URL, skipping: {source}")
            continue

        try:
            if source_type == "rss":
                items = fetch_rss(url, name)
            elif source_type == "json":
                items = fetch_json(url, name)
            elif source_type == "html":
                items = fetch_html(url, name)
            else:
                logger.warning(f"Unknown type '{source_type}' for {url}, trying RSS")
                items = fetch_rss(url, name)
            all_items.extend(items)
        except Exception as e:
            logger.warning(f"Unexpected error fetching {url}: {e}")

    logger.info(f"Total items fetched across all sources: {len(all_items)}")
    return all_items
