from __future__ import annotations

import os
import sys


def _ensure_src_path() -> None:
    root = os.path.dirname(os.path.dirname(__file__))
    src_path = os.path.join(root, "src")
    if root not in sys.path:
        sys.path.insert(0, root)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


_ensure_src_path()


def test_imports() -> None:
    import main  # noqa: F401
    import dam.ui.desktop.app  # noqa: F401
