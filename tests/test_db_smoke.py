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
