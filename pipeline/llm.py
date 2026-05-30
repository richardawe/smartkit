"""
OpenRouter LLM client — Tier 1 (free model) and Tier 2 (BYOK/model).

Reads OPENROUTER_API_KEY from the environment.
Model string comes from settings.yml (model.name).

Free-tier model availability on OpenRouter rotates. The default string below
was current at build time — update model.name in config/settings.yml if it
stops working. See https://openrouter.ai/models?q=:free for current options.

Tier 2: change model.name in settings.yml to any OpenRouter-compatible string.
To point at a different provider's base URL (e.g. OpenAI, Anthropic), add a
model.base_url key to settings.yml:
  model:
    base_url: https://api.openai.com/v1
    name: gpt-4o-mini
The Authorization header format (Bearer <key>) is compatible with OpenAI and
most OpenRouter-compatible endpoints.
"""
import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

_OPENROUTER_BASE = "https://openrouter.ai/api/v1"
_MAX_RETRIES = 2
_RETRY_BACKOFF = 2  # seconds; multiplied by attempt number


def get_api_key() -> str | None:
    return os.environ.get("OPENROUTER_API_KEY", "").strip() or None


def call_llm(prompt: str, settings: dict) -> str:
    """
    POST a chat-completion request to OpenRouter (or a configured base URL).
    Raises RuntimeError (with a human-readable message) on every failure so
    that extract.py can catch it and fall back to Tier 0. Never crashes silently.
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not set")

    model_cfg = settings.get("model", {})
    model = model_cfg.get("name", "meta-llama/llama-3.1-8b-instruct:free")
    max_tokens = int(model_cfg.get("max_tokens", 512))
    timeout = int(model_cfg.get("timeout_seconds", 30))
    base_url = model_cfg.get("base_url", _OPENROUTER_BASE).rstrip("/")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/smartkit",
        "X-Title": "SmartKit",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }

    last_err: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 2):  # attempts: 1, 2, 3
        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout,
            )

            if resp.status_code == 429:
                logger.warning(f"LLM rate-limited (attempt {attempt}/{_MAX_RETRIES + 1})")
                if attempt <= _MAX_RETRIES:
                    time.sleep(_RETRY_BACKOFF * attempt)
                    continue
                raise RuntimeError(f"Rate-limited after {_MAX_RETRIES + 1} attempts")

            if resp.status_code == 401:
                raise RuntimeError("Invalid or missing API key (HTTP 401)")

            if resp.status_code == 404:
                raise RuntimeError(
                    f"Model not found: {model!r} (HTTP 404) — "
                    "update model.name in config/settings.yml"
                )

            resp.raise_for_status()

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            logger.info(f"LLM response received ({len(content)} chars, model={model})")
            return content

        except RuntimeError:
            raise  # already descriptive — don't retry
        except (requests.Timeout, requests.ConnectionError) as e:
            logger.warning(f"LLM network error (attempt {attempt}): {e}")
            last_err = e
            if attempt <= _MAX_RETRIES:
                time.sleep(_RETRY_BACKOFF * attempt)
        except Exception as e:
            last_err = e
            break

    raise RuntimeError(f"LLM call failed after {_MAX_RETRIES + 1} attempts: {last_err}")
