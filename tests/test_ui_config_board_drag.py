from __future__ import annotations

import os
import sys
from types import SimpleNamespace

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

from dam.core.services.config_service import ConfigService  # noqa: E402
from dam.infra.db import init_db  # noqa: E402
from dam.infra.repositories import ConfigRepository  # noqa: E402
from dam.ui.desktop.views.config_board import ConfigBoard  # noqa: E402


def test_config_board_drag_updates_position() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk is not available in this environment")
        return

    conn = init_db(":memory:")
    try:
        root.withdraw()
        config_service = ConfigService(ConfigRepository(conn))
        config_a = config_service.create_config("Config A")
        config_service.create_config("Config B")

        board = ConfigBoard(root, config_service)
        board.pack(fill="both", expand=True)
        board.refresh()

        root.update_idletasks()
        root.update()

        window_id = board._card_windows[config_a.config_id]
        x0, y0 = board.canvas.coords(window_id)

        root_x = board.canvas.winfo_rootx()
        root_y = board.canvas.winfo_rooty()
        start_event = SimpleNamespace(x_root=int(root_x + x0 + 10), y_root=int(root_y + y0 + 10))
        board._start_drag(start_event, config_a.config_id)

        drag_event = SimpleNamespace(x_root=int(root_x + x0 + 110), y_root=int(root_y + y0 + 120))
        board._on_drag(drag_event)

        x1, y1 = board._positions[config_a.config_id]
        assert (x1, y1) != (int(x0), int(y0))
    finally:
        conn.close()
        root.destroy()
