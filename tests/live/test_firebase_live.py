"""
NaviStudo Backend - Live Firebase connection tests.

These tests are kept separate from the ordinary mocked unit tests. They are
skipped unless ``NAVISTUDO_LIVE_TESTS`` is set to a truthy value, so they never
run against production data by accident.

They are strictly READ-ONLY: no documents are created, updated, or deleted.

Run them with:

    set NAVISTUDO_LIVE_TESTS=1
    set GOOGLE_APPLICATION_CREDENTIALS=%USERPROFILE%\\Downloads\\navistudo-firebase-adminsdk-fbsvc-f5f7bf9956.json
    pytest tests\\live -v
"""

from __future__ import annotations

import os

import pytest

LIVE = os.environ.get("NAVISTUDO_LIVE_TESTS", "").lower() in ("1", "true", "yes")

pytestmark = pytest.mark.skipif(
    not LIVE,
    reason="Live Firebase tests are opt-in (set NAVISTUDO_LIVE_TESTS=1).",
)


def _require_credentials() -> None:
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return
    if all(
        os.environ.get(k)
        for k in ("FIREBASE_PROJECT_ID", "FIREBASE_CLIENT_EMAIL", "FIREBASE_PRIVATE_KEY")
    ):
        return
    pytest.skip("No Firebase credentials configured for the live test.")


def test_firebase_admin_initializes():
    _require_credentials()
    import firebase_admin
    from firebase_admin import credentials

    if firebase_admin._apps:
        app = firebase_admin.get_app()
    elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        app = firebase_admin.initialize_app(
            credentials.Certificate(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
        )
    else:
        app = firebase_admin.initialize_app()

    assert app is not None


def test_firestore_read_only_access():
    _require_credentials()
    import firebase_admin
    from firebase_admin import firestore

    if firebase_admin._apps:
        app = firebase_admin.get_app()
    else:
        app = firebase_admin.initialize_app()

    db = firestore.client(app=app)

    # Read-only metadata access.
    collection_ids = [c.id for c in db.collections()]
    assert isinstance(collection_ids, list)

    # Read-only document access (at most one document, no writes).
    smoke_collection = os.environ.get("FIRESTORE_SMOKE_COLLECTION", "students")
    docs = list(db.collection(smoke_collection).limit(1).get())
    assert isinstance(docs, list)
