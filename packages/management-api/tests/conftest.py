"""Importing `cofy.management` builds its FastAPI `app` (and its default file-backed
persistence) at import time, so `COFY_MANAGEMENT_DATA_DIR` must already be set before test
collection imports anything from that package - even tests that never touch this default,
since most tests point their own persistence at a `tmp_path` instead."""

import os
import tempfile

os.environ.setdefault("COFY_MANAGEMENT_DATA_DIR", tempfile.mkdtemp(prefix="cofy-management-tests-"))
