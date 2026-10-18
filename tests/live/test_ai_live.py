"""
NaviStudo Backend - opt-in live AI provider tests.

Skipped unless ``NAVISTUDO_AI_LIVE_TESTS`` is set to a truthy value, so they
never run by accident.

The module-scoped fixture performs at most ONE provider request in total (no
retries), and does not run the recommendation pipeline.

Run with:

    set NAVISTUDO_AI_LIVE_TESTS=1
    set OPENAI_API_KEY=sk-...
    pytest tests\\live -v
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

LIVE = os.environ.get("NAVISTUDO_AI_LIVE_TESTS", "").lower() in ("1", "true", "yes")

pytestmark = pytest.mark.skipif(
    not LIVE,
    reason="Live AI tests are opt-in (set NAVISTUDO_AI_LIVE_TESTS=1).",
)


@pytest.fixture(scope="module")
def ai_live_response():
    try:
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
    except Exception:  # noqa: BLE001 - .env is optional
        pass

    key = os.environ.get("AI_MODEL_ONE_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        pytest.skip("No AI provider API key configured for the live test.")

    from app.ai_client import OpenAICompatibleClient

    client = OpenAICompatibleClient(api_key=key, default_timeout=15, max_retries=0)
    return client.call(
        system_prompt="You are a connectivity test.",
        user_prompt='Reply with exactly this JSON object and nothing else: {"ok": true}',
        temperature=0.0,
        timeout=15,
        response_format={"type": "json_object"},
        max_tokens=16,
    )


def test_ai_provider_reachable(ai_live_response):
    assert isinstance(ai_live_response, dict)
