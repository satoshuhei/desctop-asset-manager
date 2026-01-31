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


def test_drag_payload_roundtrip() -> None:
    pytest.importorskip("PySide6")
    from dam.ui.desktop.app import _decode_drag, _encode_drag

    payload = _encode_drag("device", 42, None)
    assert _decode_drag(payload) == ("device", 42, None)

    payload = _encode_drag("license", 7, 3)
    assert _decode_drag(payload) == ("license", 7, 3)


def test_config_canvas_creates_cards(tmp_path: Path) -> None:
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets

    from dam.core.services.asset_service import AssetService
    from dam.core.services.config_service import ConfigService
    from dam.infra.db import init_db
    from dam.infra.repositories import ConfigRepository, DeviceRepository, LicenseRepository
    from dam.ui.desktop.app import ConfigCanvasWidget

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    conn = init_db(":memory:")
    asset_service = AssetService(DeviceRepository(conn), LicenseRepository(conn))
    config_service = ConfigService(ConfigRepository(conn))

    widget = ConfigCanvasWidget(config_service, on_refresh_assets=lambda: asset_service.list_devices())
    config_service.create_config(name="Config Demo")
    widget.refresh()

    assert widget._proxies

    widget.deleteLater()
    app.processEvents()
