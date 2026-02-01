from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class CanvasState:
    scale: float
    center_x: float
    center_y: float


class UIStateStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ui_config_positions (
                config_id INTEGER PRIMARY KEY,
                x REAL NOT NULL,
                y REAL NOT NULL,
                hidden INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ui_canvas_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                scale REAL NOT NULL,
                center_x REAL NOT NULL,
                center_y REAL NOT NULL
            )
            """
        )
        self._conn.commit()

    def load_positions(self) -> Dict[int, tuple[float, float, bool]]:
        cur = self._conn.execute("SELECT config_id, x, y, hidden FROM ui_config_positions")
        return {int(row[0]): (float(row[1]), float(row[2]), bool(row[3])) for row in cur.fetchall()}

    def save_position(self, config_id: int, x: float, y: float) -> None:
        self._conn.execute(
            """
            INSERT INTO ui_config_positions (config_id, x, y, hidden)
            VALUES (?, ?, ?, COALESCE((SELECT hidden FROM ui_config_positions WHERE config_id = ?), 0))
            ON CONFLICT(config_id) DO UPDATE SET x = excluded.x, y = excluded.y
            """,
            (config_id, x, y, config_id),
        )
        self._conn.commit()

    def set_hidden(self, config_id: int, hidden: bool) -> None:
        self._conn.execute(
            """
            INSERT INTO ui_config_positions (config_id, x, y, hidden)
            VALUES (?, 0, 0, ?)
            ON CONFLICT(config_id) DO UPDATE SET hidden = excluded.hidden
            """,
            (config_id, int(hidden)),
        )
        self._conn.commit()

    def load_canvas_state(self) -> Optional[CanvasState]:
        cur = self._conn.execute("SELECT scale, center_x, center_y FROM ui_canvas_state WHERE id = 1")
        row = cur.fetchone()
        if row is None:
            return None
        return CanvasState(scale=float(row[0]), center_x=float(row[1]), center_y=float(row[2]))

    def save_canvas_state(self, state: CanvasState) -> None:
        self._conn.execute(
            """
            INSERT INTO ui_canvas_state (id, scale, center_x, center_y)
            VALUES (1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET scale = excluded.scale, center_x = excluded.center_x, center_y = excluded.center_y
            """,
            (state.scale, state.center_x, state.center_y),
        )
        self._conn.commit()


def ui_state_db_path(base_path: str) -> str:
    if base_path == ":memory:":
        return ":memory:"
    path = Path(base_path).resolve()
    return str(path)
