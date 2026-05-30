"""
OpenRouter LLM client — Phase 1 stub.
Phase 2 implements Tier 1/2 with retry, timeout, JSON-schema validation,
and automatic fallback to Tier 0 on any failure.
"""
# v2: full OpenRouter client with OPENROUTER_API_KEY, configurable model,
#     timeout+retry, required-field schema validation, and graceful fallback
#     to extract.extract_tier0() will be implemented here in Phase 2.


def call_llm(prompt: str, settings: dict) -> str:
    """
    Call the configured LLM via OpenRouter.
    Phase 1 stub — always raises NotImplementedError.
    """
    raise NotImplementedError("LLM client not implemented until Phase 2")
