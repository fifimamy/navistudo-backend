"""
NaviStudo Backend - Common Exceptions.

Centralized exception classes to avoid duplication and circular imports.
"""

from typing import Any


class NaviStudoError(Exception):
    """Base exception for all NaviStudo backend errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.details = details or {}
        super().__init__(message)


class FirebaseError(NaviStudoError):
    """Raised when Firebase operations fail."""

    def __init__(self, message: str, original_error: Exception | None = None):
        details = {"original_error": str(original_error)} if original_error else {}
        super().__init__(message, details)
        self.original_error = original_error


class StudentNotFoundError(NaviStudoError):
    """Raised when a student profile is not found in Firebase."""

    def __init__(self, uid: str):
        super().__init__(f"Student profile not found for UID: {uid}", {"uid": uid})
        self.uid = uid


class ValidationError(NaviStudoError):
    """Raised when data validation fails (e.g., Model 2 output validation)."""

    pass


class ModelOneError(NaviStudoError):
    """Raised when Model 1 processing fails."""

    pass


class ModelTwoError(NaviStudoError):
    """Raised when Model 2 processing fails."""

    pass


class ServiceNotImplementedError(NaviStudoError):
    """Raised when a required component is not yet implemented."""

    pass