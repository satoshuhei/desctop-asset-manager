from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import tkinter as tk


def _ensure_src_path() -> None:
    root = os.path.dirname(os.path.dirname(__file__))
    src_path = os.path.join(root, "src")
    if root not in sys.path:
        sys.path.insert(0, root)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


_ensure_src_path()

from dam.ui.desktop.app import DesktopApp  # noqa: E402


def test_app_startup_smoke(tmp_path: Path) -> None:
    try:
        app = DesktopApp(db_path=str(tmp_path / "test.db"))
    except tk.TclError:
        pytest.skip("Tk is not available in this environment")
        return

    try:
        app.root.update_idletasks()
        app.root.update()
    finally:
        app.root.destroy()
