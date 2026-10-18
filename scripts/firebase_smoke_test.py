"""
NaviStudo Backend - Live Firebase connection smoke test.

Standalone, READ-ONLY verification that Firebase Admin initializes and that
Firestore can be reached. It never creates, updates, or deletes documents and
never prints credentials, private keys, tokens, or the service-account JSON.

Usage (Windows CMD):

    set GOOGLE_APPLICATION_CREDENTIALS=%USERPROFILE%\\Downloads\\navistudo-firebase-adminsdk-fbsvc-f5f7bf9956.json
    python scripts\\firebase_smoke_test.py

Exit codes:
    0  success (Firebase initialized and a read-only Firestore call succeeded)
    2  credentials missing / not configured
    3  Firebase Admin initialization failed
    4  Firestore read-only access failed
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _credentials_source() -> tuple[str, Path | None]:
    """Return (description, path) for the configured credentials, without values."""
    gac = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if gac:
        return "GOOGLE_APPLICATION_CREDENTIALS", Path(gac)
    if all(
        os.environ.get(k)
        for k in ("FIREBASE_PROJECT_ID", "FIREBASE_CLIENT_EMAIL", "FIREBASE_PRIVATE_KEY")
    ):
        return "FIREBASE_* environment variables", None
    return "", None


def _validate_service_account_file(path: Path) -> list[str]:
    """Return a list of structural problems (never the values)."""
    problems: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 - report only, do not leak contents
        return [f"service-account file is not valid JSON ({type(e).__name__})"]

    if not isinstance(data, dict):
        return ["service-account file is not a JSON object"]

    required = {"type", "project_id", "client_email", "private_key"}
    missing = sorted(required - set(data))
    if missing:
        problems.append(f"service-account file is missing key(s): {missing}")
    if data.get("type") != "service_account":
        problems.append("service-account 'type' is not 'service_account'")
    return problems


def main() -> int:
    source, path = _credentials_source()

    if not source:
        print("FAIL: No Firebase credentials are configured.")
        print("Set GOOGLE_APPLICATION_CREDENTIALS to the service-account JSON path,")
        print("or set FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL and FIREBASE_PRIVATE_KEY.")
        return 2

    if path is not None:
        if not path.is_file():
            print(f"FAIL: GOOGLE_APPLICATION_CREDENTIALS points to a missing file: {path}")
            return 2
        problems = _validate_service_account_file(path)
        if problems:
            for problem in problems:
                print(f"FAIL: {problem}")
            return 2
        # Do not print the path's contents or the credentials themselves.
        print("Credentials source: GOOGLE_APPLICATION_CREDENTIALS (file present, contents not printed).")
    else:
        print("Credentials source: FIREBASE_* environment variables.")

    # Import after credentials are validated so failures are reported clearly.
    import firebase_admin
    from firebase_admin import credentials, firestore

    try:
        if firebase_admin._apps:
            app = firebase_admin.get_app()
        elif path is not None:
            app = firebase_admin.initialize_app(credentials.Certificate(str(path)))
        else:
            app = firebase_admin.initialize_app()
    except Exception as e:  # noqa: BLE001 - surface the error type, not secrets
        print(f"FAIL: Firebase Admin initialization failed ({type(e).__name__}): {e}")
        return 3

    db = firestore.client(app=app)
    # firebase-admin does not always populate app.options.project_id from the
    # certificate; the Firestore client resolves the project from the credential.
    cred_project = None
    if path is not None:
        try:
            cred_project = json.loads(path.read_text(encoding="utf-8")).get("project_id")
        except Exception:  # noqa: BLE001
            cred_project = None

    print(
        "Firebase Admin initialized. "
        f"credential project_id present: {bool(cred_project)}; "
        f"Firestore client project present: {bool(getattr(db, 'project', None))}."
    )

    # Read-only access #1: list collections (metadata only).
    try:
        collection_ids = [c.id for c in db.collections()]
        print(f"Read-only Firestore access OK. collections found: {len(collection_ids)}")
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: Firestore collection listing failed ({type(e).__name__}): {e}")
        return 4

    # Read-only access #2: read at most one document from a configurable collection.
    smoke_collection = os.environ.get("FIRESTORE_SMOKE_COLLECTION", "students")
    try:
        docs = list(db.collection(smoke_collection).limit(1).get())
        print(
            f"Read-only document read OK from '{smoke_collection}' "
            f"({len(docs)} document(s) read, no writes performed)."
        )
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: Firestore document read failed ({type(e).__name__}): {e}")
        return 4

    print("SUCCESS: Firebase Admin initialized and Firestore read-only access verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
