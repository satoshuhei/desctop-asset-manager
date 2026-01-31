from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


def _ensure_src_path() -> None:
    root = os.path.dirname(os.path.dirname(__file__))
    src_path = os.path.join(root, "src")
    if root not in sys.path:
        sys.path.insert(0, root)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


_ensure_src_path()


def test_app_startup_smoke(tmp_path: Path) -> None:
    try:
        from PySide6 import QtWidgets  # noqa: WPS433
    except Exception:
        pytest.skip("PySide6 is not available in this environment")
        return

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from dam.ui.desktop.app import DesktopApp  # noqa: E402
    window = DesktopApp(db_path=str(tmp_path / "test.db"))
    window.show()
    app.processEvents()
    window.close()
