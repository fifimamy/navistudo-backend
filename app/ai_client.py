"""
NaviStudo Backend - AI Provider Client.

Real AI provider client supporting OpenAI-compatible APIs with structured
output, timeouts, retries, and safe error handling.

Configured via environment variables:
- OPENAI_API_KEY: API key for OpenAI or compatible provider
- OPENAI_API_BASE: Custom API base URL (optional)
- AI_MODEL_ONE_NAME: Model name for Model 1 (default: gpt-4o-mini)
- AI_MODEL_TWO_NAME: Model name for Model 2 (default: gpt-4o-mini)
"""

import json
import logging
import re
import time
from typing import Any
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)


class AIProviderError(Exception):
    """Raised when AI provider operations fail."""
    pass


class AIProviderHTTPError(AIProviderError):
    """Raised when the provider returns an HTTP error.

    Carries the HTTP status and a sanitized message parsed from the response
    body so callers can distinguish credential problems from permission
    problems without exposing secrets.

    Attributes:
        status: HTTP status code, if known.
        reason: short HTTP reason phrase.
        api_message: sanitized message from the response body, if any.
        api_type: error type from the body, if any.
        api_code: error code from the body, if any.
    """

    def __init__(
        self,
        status: int | None,
        reason: str = "",
        message: str | None = None,
        type: str | None = None,
        code: str | None = None,
    ) -> None:
        self.status = status
        self.reason = reason
        self.api_message = message
        self.api_type = type
        self.api_code = code

        parts: list[str] = []
        if status is not None:
            parts.append(f"HTTP {status}")
        if reason:
            parts.append(reason)
        if message:
            parts.append(f"- {message}")
        if type:
            parts.append(f"(type: {type})")
        if code:
            parts.append(f"(code: {code})")
        super().__init__(": ".join(parts) if parts else "AI provider HTTP error")


class OpenAICompatibleClient:
    """AI provider client for OpenAI-compatible APIs.

    Uses urllib (standard library) to avoid external dependencies.
    Supports structured JSON output and configurable timeouts.
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        default_timeout: int = 30,
        max_retries: int = 2,
    ):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._api_base = (
            api_base
            or os.environ.get("OPENAI_API_BASE")
            or "https://api.openai.com/v1"
        ).rstrip("/")
        self._default_timeout = default_timeout
        self._max_retries = max_retries

    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        timeout: int = 30,
        response_format: dict[str, Any] | None = None,
        model: str | None = None,
        max_tokens: int = 4000,
    ) -> dict[str, Any]:
        """Call the AI provider and return parsed JSON response.

        Args:
            system_prompt: System prompt defining the model's role.
            user_prompt: User prompt with input data.
            temperature: Sampling temperature.
            timeout: Request timeout in seconds.
            response_format: Optional response format (e.g., {"type": "json_object"}).
            model: Model name override.
            max_tokens: Maximum completion tokens (keep small for smoke tests).

        Returns:
            Parsed JSON response as a dictionary.

        Raises:
            AIProviderError: If the provider call fails after all retries.
        """
        if not self._api_key:
            raise AIProviderError("AI provider API key not configured (OPENAI_API_KEY)")

        model = model or "gpt-4o-mini"

        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            payload["response_format"] = response_format

        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                return self._make_request(payload, timeout)
            except (HTTPError, URLError, TimeoutError) as e:
                last_error = e
                logger.warning(
                    "AI provider call failed (attempt %d/%d): %s",
                    attempt + 1,
                    self._max_retries + 1,
                    e,
                )
                if attempt < self._max_retries:
                    time.sleep(1)
            except Exception as e:
                last_error = e
                logger.error("AI provider unexpected error: %s", e)
                break

        raise AIProviderError(
            f"AI provider failed after {self._max_retries + 1} attempts: {last_error}"
        )

    def _make_request(self, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
        """Make a single request to the AI provider."""
        data = json.dumps(payload).encode("utf-8")
        req = urlrequest.Request(
            f"{self._api_base}/chat/completions",
            data=data,
            method="POST",
        )
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self._api_key}")

        with self._open(req, timeout) as response:
            body = response.read().decode("utf-8")
            result = json.loads(body)

        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            raise AIProviderError("AI provider returned empty response")

        # Parse JSON content (handle potential markdown code fences)
        parsed = self._parse_json_response(content)
        return parsed

    @staticmethod
    def _parse_json_response(content: str) -> dict[str, Any]:
        """Parse JSON from model response, handling code fences."""
        text = content.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```) and last line (```)
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            text = "\n".join(lines).strip()

        return json.loads(text)

    _SECRET_PATTERNS = (
        re.compile(r"\bsk-[A-Za-z0-9_\-]{6,}"),
        re.compile(r"\bgsk_[A-Za-z0-9_\-]{6,}"),
        re.compile(r"\bBearer\s+[A-Za-z0-9._\-]+"),
        re.compile(r"\b[A-Za-z0-9_\-]{40,}"),
    )

    @classmethod
    def _sanitize_error_text(cls, text: str) -> str:
        """Redact anything that could be a secret before it is shown."""
        if not text:
            return ""
        cleaned = str(text)
        for pattern in cls._SECRET_PATTERNS:
            cleaned = pattern.sub("[REDACTED]", cleaned)
        return cleaned.strip()

    @classmethod
    def _parse_error_body(cls, body: str) -> dict[str, str | None]:
        """Parse an OpenAI-compatible error body into safe, sanitized fields."""
        empty = {"message": None, "type": None, "code": None}
        if not body:
            return empty
        try:
            data = json.loads(body)
        except Exception:  # noqa: BLE001 - fall back to the raw text
            return {
                "message": cls._sanitize_error_text(body)[:500] or None,
                "type": None,
                "code": None,
            }

        err = data.get("error") if isinstance(data, dict) else None
        if isinstance(err, dict):
            return {
                "message": cls._sanitize_error_text(str(err.get("message", "")))[:500] or None,
                "type": cls._sanitize_error_text(str(err.get("type", "")))[:200] or None,
                "code": cls._sanitize_error_text(str(err.get("code", "")))[:200] or None,
            }
        if isinstance(err, str):
            return {
                "message": cls._sanitize_error_text(err)[:500] or None,
                "type": None,
                "code": None,
            }
        return {
            "message": cls._sanitize_error_text(body)[:500] or None,
            "type": None,
            "code": None,
        }

    def _open(self, req: "urlrequest.Request", timeout: int):
        """Open a request, converting HTTP errors into AIProviderHTTPError.

        The response body is read and sanitized so the status and provider
        message can be surfaced without leaking the Authorization header or key.
        """
        try:
            return urlrequest.urlopen(req, timeout=timeout)
        except HTTPError as e:
            raw = ""
            try:
                raw = e.read().decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001 - body may be unavailable
                raw = ""
            details = self._parse_error_body(raw)
            raise AIProviderHTTPError(
                status=getattr(e, "code", None),
                reason=getattr(e, "reason", "") or "",
                **details,
            ) from e

    def list_models(self, timeout: int = 15) -> list[str]:
        """Return the model IDs advertised by the provider.

        This is a read-only ``GET /models`` call (no inference, no cost). It is
        useful for verifying which model identifiers the account can actually
        use before making an inference request.
        """
        if not self._api_key:
            raise AIProviderError("AI provider API key not configured (OPENAI_API_KEY)")
        req = urlrequest.Request(f"{self._api_base}/models", method="GET")
        req.add_header("Accept", "application/json")
        req.add_header("Authorization", f"Bearer {self._api_key}")
        with self._open(req, timeout) as response:
            body = response.read().decode("utf-8")
        data = json.loads(body)
        return [
            m.get("id")
            for m in data.get("data", [])
            if isinstance(m, dict) and m.get("id")
        ]


# Import os here to avoid issues with module-level imports
import os


def get_ai_client() -> OpenAICompatibleClient:
    """Get a configured AI provider client.

    Returns:
        OpenAICompatibleClient instance configured from environment variables.

    Raises:
        AIProviderError: If OPENAI_API_KEY is not set.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise AIProviderError(
            "OPENAI_API_KEY not set. Provide a valid API key to enable real AI calls."
        )
    return OpenAICompatibleClient(api_key=api_key)
