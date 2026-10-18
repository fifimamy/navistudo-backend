"""
NaviStudo Backend - Live AI provider smoke test.

Makes at most ONE minimal chat-completion request to verify that the configured
provider is reachable and the API key works. It does NOT run the recommendation
pipeline and does NOT call both models.

It never prints the API key, any credential, or the response content.

The test loads the repository-root ``.env`` file (if present) so it works with
the existing local setup; exported environment variables take precedence.

Usage (Windows CMD):

    python scripts\\ai_smoke_test.py

Free model-list check (GET /models, no inference request):

    python scripts\\ai_smoke_test.py --list-models

If the key is not present in the environment or ``.env``, the script exits with
code 2 and makes NO network request.

Exit codes:
    0  success (one live request completed, or the model list was retrieved)
    2  configuration missing (NO network request was made)
    3  request failed
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow running this script directly from the repository root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

DEFAULT_BASE = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"

_STATUS_HINTS = {
    400: "Bad request: check the request payload / response_format support.",
    401: "Invalid or missing credentials (bad or expired API key).",
    403: (
        "Authenticated but not authorized: account/project permission "
        "restriction, model not permitted for this key, or region restriction."
    ),
    404: "Endpoint not found: check OPENAI_API_BASE (expected .../openai/v1).",
    429: "Rate limited: retry later or check plan limits.",
    500: "Provider server error.",
    502: "Provider bad gateway: retry later.",
    503: "Provider unavailable: retry later.",
}


def _print_http_diagnostic(exc: Exception) -> None:
    """Print a sanitized HTTP diagnostic (status + provider message + hint)."""
    status = getattr(exc, "status", None)
    if status is None:
        print(f"FAIL: request failed ({type(exc).__name__}): {exc}")
        return

    print(f"HTTP status: {status}")
    reason = getattr(exc, "reason", "")
    if reason:
        print(f"Reason: {reason}")
    message = getattr(exc, "api_message", None)
    if message:
        print(f"API error message: {message}")
    error_type = getattr(exc, "api_type", None)
    if error_type:
        print(f"API error type: {error_type}")
    error_code = getattr(exc, "api_code", None)
    if error_code:
        print(f"API error code: {error_code}")
    hint = _STATUS_HINTS.get(status)
    if hint:
        print(f"Likely cause: {hint}")


def _load_dotenv() -> None:
    """Load the repository-root .env if present (never raises)."""
    try:
        from dotenv import load_dotenv

        load_dotenv(_REPO_ROOT / ".env")
    except Exception:  # noqa: BLE001 - .env is optional
        pass


def _resolve_key() -> str | None:
    return os.environ.get("AI_MODEL_ONE_API_KEY") or os.environ.get("OPENAI_API_KEY")


def _list_models_only(argv: list[str]) -> bool:
    return "--list-models" in argv


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    _load_dotenv()
    key = _resolve_key()
    if not key:
        print("FAIL: No AI provider API key is configured.")
        print("Set one of the following environment variables:")
        print("  OPENAI_API_KEY          (used by both models)")
        print("  AI_MODEL_ONE_API_KEY    (Model 1 only)")
        print("No network request was made.")
        return 2

    base = os.environ.get("OPENAI_API_BASE", DEFAULT_BASE).rstrip("/")
    model = os.environ.get("AI_MODEL_ONE_NAME", DEFAULT_MODEL)
    timeout = 15

    # Report only non-secret configuration.
    print(f"Provider base: {base}")
    print(f"Model: {model}")
    print(
        "API key: configured (value not printed). "
        f"timeout={timeout}s, max_tokens=16, retries=0"
    )

    from app.ai_client import OpenAICompatibleClient

    client = OpenAICompatibleClient(
        api_key=key, api_base=base, default_timeout=timeout, max_retries=0
    )

    # Free, read-only model listing: no inference request is made.
    if _list_models_only(argv):
        try:
            model_ids = client.list_models(timeout=timeout)
        except Exception as e:  # noqa: BLE001 - print a sanitized diagnostic
            print("FAIL: listing models failed.")
            _print_http_diagnostic(e)
            return 3
        print(
            f"SUCCESS: provider reachable. {len(model_ids)} model(s) listed "
            "(no inference request made)."
        )
        for model_id in model_ids:
            print(f"  - {model_id}")
        return 0

    try:
        parsed = client.call(
            system_prompt="You are a connectivity test.",
            user_prompt='Reply with exactly this JSON object and nothing else: {"ok": true}',
            temperature=0.0,
            timeout=timeout,
            response_format={"type": "json_object"},
            model=model,
            max_tokens=16,
        )
    except Exception as e:  # noqa: BLE001 - print a sanitized diagnostic
        print("FAIL: AI provider request failed.")
        _print_http_diagnostic(e)
        return 3

    print(f"SUCCESS: AI provider reachable. Parsed JSON keys: {sorted(parsed.keys())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
