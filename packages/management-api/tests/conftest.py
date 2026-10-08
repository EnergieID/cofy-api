"""Importing `cofy.management` builds its FastAPI `app` (and its default file-backed
persistence) at import time, so the data directories, the login configuration and the communities' URL must
already be set before test collection imports anything from that package - even tests that
never touch this default, since most tests point their own persistence at a `tmp_path` instead."""

import os
import tempfile

os.environ.setdefault("COFY_MANAGEMENT_DATA_DIR", tempfile.mkdtemp(prefix="cofy-management-tests-"))
os.environ.setdefault("COFY_MANAGEMENT_COMMUNITIES_DIR", tempfile.mkdtemp(prefix="cofy-management-communities-"))
os.environ.setdefault("COFY_MANAGEMENT_OIDC_ISSUER", "https://identity.example")
os.environ.setdefault("COFY_MANAGEMENT_OIDC_CLIENT_ID", "cofy-management")
os.environ.setdefault("COFY_MANAGEMENT_OIDC_CLIENT_SECRET", "client-secret")
os.environ.setdefault("COFY_MANAGEMENT_SESSION_SECRET", "session-secret")
os.environ.setdefault("COFY_MANAGEMENT_COMMUNITIES_URL", "https://cofy.example/communities")
