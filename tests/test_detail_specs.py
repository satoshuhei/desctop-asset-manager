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

from dam.core.services.asset_service import AssetService  # noqa: E402
from dam.core.services.config_service import ConfigService  # noqa: E402
from dam.infra.db import init_db  # noqa: E402
from dam.infra.repositories import ConfigRepository, DeviceRepository, LicenseRepository  # noqa: E402
from dam.ui.ui_state import CanvasState, UIStateStore  # noqa: E402


def test_config_no_auto_generation() -> None:
    conn = init_db(":memory:")
    try:
        repo = ConfigRepository(conn)
        next_id = conn.execute("SELECT COALESCE(MAX(config_id), 0) + 1 FROM configurations").fetchone()[0]
        expected = f"CNFG-{int(next_id):03d}"
        config = repo.create(name="Auto Config", note="")
        assert config.config_no == expected
        assert config.created_at
        assert config.updated_at
    finally:
        conn.close()


def test_assign_license_rejects_second_config() -> None:
    conn = init_db(":memory:")
    try:
        asset_service = AssetService(DeviceRepository(conn), LicenseRepository(conn))
        config_service = ConfigService(ConfigRepository(conn))

        license_item = asset_service.add_license(
            license_no="LIC-X",
            name="License X",
            license_key="LIC-X",
            state="active",
            note="spec",
        )
        config_a = config_service.create_config(name="Config A")
        config_b = config_service.create_config(name="Config B")

        config_service.assign_license(config_a.config_id, license_item.license_id)
        with pytest.raises(ValueError):
            config_service.assign_license(config_b.config_id, license_item.license_id)

        licenses_a = config_service.list_config_licenses(config_a.config_id)
        licenses_b = config_service.list_config_licenses(config_b.config_id)

        assert any(l.license_id == license_item.license_id for l in licenses_a)
        assert all(l.license_id != license_item.license_id for l in licenses_b)
    finally:
        conn.close()


def test_ui_state_store_positions_and_hidden(tmp_path: Path) -> None:
    db_path = str(tmp_path / "ui_state.db")
    store = UIStateStore(db_path)
    store.set_hidden(101, True)
    store.save_position(101, 120.5, 80.25)
    store.save_position(202, 10.0, 20.0)
    store.set_hidden(202, False)

    store_reloaded = UIStateStore(db_path)
    positions = store_reloaded.load_positions()

    assert positions[101] == (120.5, 80.25, True)
    assert positions[202] == (10.0, 20.0, False)


def test_ui_state_store_canvas_state_roundtrip(tmp_path: Path) -> None:
    db_path = str(tmp_path / "ui_state.db")
    store = UIStateStore(db_path)
    state = CanvasState(scale=1.25, center_x=100.0, center_y=200.0)
    store.save_canvas_state(state)

    store_reloaded = UIStateStore(db_path)
    loaded = store_reloaded.load_canvas_state()

    assert loaded == state
