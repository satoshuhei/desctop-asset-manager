from __future__ import annotations

import os
import sys


def _ensure_src_path() -> None:
    root = os.path.dirname(os.path.dirname(__file__))
    src_path = os.path.join(root, "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


_ensure_src_path()


def test_init_db_smoke() -> None:
    from dam.infra.db import init_db

    conn = init_db(":memory:")
    conn.close()


def test_init_db_seeds_sample_data() -> None:
    from dam.infra.db import init_db

    conn = init_db(":memory:")
    try:
        device_count = conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
        license_count = conn.execute("SELECT COUNT(*) FROM licenses").fetchone()[0]
        assert device_count > 0
        assert license_count > 0
    finally:
        conn.close()
