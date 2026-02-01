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


def test_config_canvas_arrange_sorts_by_config_no(tmp_path: Path) -> None:
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

    config_b = config_service.create_config(name="Config B", config_no="CNFG-002")
    config_a = config_service.create_config(name="Config A", config_no="CNFG-001")

    widget = ConfigCanvasWidget(config_service, on_refresh_assets=lambda: asset_service.list_devices())
    widget.resize(1200, 800)
    widget.show()
    app.processEvents()

    widget.refresh()
    widget._arrange_cards("row")

    pos_a = widget._proxies[config_a.config_id].pos()
    pos_b = widget._proxies[config_b.config_id].pos()

    layout_order = sorted(
        [
            (config_a.config_id, pos_a),
            (config_b.config_id, pos_b),
        ],
        key=lambda item: (item[1].y(), item[1].x()),
    )
    ordered_ids = [item[0] for item in layout_order]
    assert ordered_ids == [config_a.config_id, config_b.config_id]

    widget.deleteLater()
    app.processEvents()


def test_tables_resize_columns_to_contents(tmp_path: Path) -> None:
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets

    from dam.core.services.asset_service import AssetService
    from dam.core.services.config_service import ConfigService
    from dam.infra.db import init_db
    from dam.infra.repositories import ConfigRepository, DeviceRepository, LicenseRepository
    from dam.ui.desktop.app import ConfigCanvasWidget, DevicePanel, LicensePanel

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    conn = init_db(":memory:")
    asset_service = AssetService(DeviceRepository(conn), LicenseRepository(conn))
    config_service = ConfigService(ConfigRepository(conn))

    device_panel = DevicePanel(asset_service, toast=None)
    license_panel = LicensePanel(asset_service, toast=None)

    device_panel.refresh()
    license_panel.refresh()

    device_header = device_panel.device_table.horizontalHeader()
    license_header = license_panel.license_table.horizontalHeader()

    assert device_header.sectionResizeMode(0) == QtWidgets.QHeaderView.ResizeMode.ResizeToContents
    assert license_header.sectionResizeMode(0) == QtWidgets.QHeaderView.ResizeMode.ResizeToContents

    canvas = ConfigCanvasWidget(config_service, on_refresh_assets=lambda: asset_service.list_devices())
    config = config_service.create_config(name="Config A")
    canvas.refresh()
    canvas.scene.clearSelection()
    proxy = canvas._proxies[config.config_id]
    proxy.setSelected(True)
    app.processEvents()

    detail_header = canvas.detail_devices.horizontalHeader()
    assert detail_header.sectionResizeMode(0) == QtWidgets.QHeaderView.ResizeMode.ResizeToContents

    device_panel.deleteLater()
    license_panel.deleteLater()
    canvas.deleteLater()
    app.processEvents()


def test_config_detail_title_is_visible(tmp_path: Path) -> None:
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets

    from dam.core.services.config_service import ConfigService
    from dam.infra.db import init_db
    from dam.infra.repositories import ConfigRepository
    from dam.ui.desktop.app import ConfigCanvasWidget
    from dam.ui.i18n import tr

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    conn = init_db(":memory:")
    config_service = ConfigService(ConfigRepository(conn))

    widget = ConfigCanvasWidget(config_service, on_refresh_assets=lambda: None)
    widget.show()
    app.processEvents()

    labels = [label.text() for label in widget.findChildren(QtWidgets.QLabel)]
    assert tr("Configuration Details") in labels

    widget.deleteLater()
    app.processEvents()


def test_pane_title_has_background_style(tmp_path: Path) -> None:
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    from dam.ui.desktop.app import DesktopApp

    window = DesktopApp(db_path=str(tmp_path / "test.db"))
    style = window.styleSheet()

    assert "QFrame#PaneTitleBar" in style
    assert "QLabel#PaneTitleText" in style
    assert "background-color" in style

    window.close()


def test_pane_titles_use_theme_only(tmp_path: Path) -> None:
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    from dam.ui.desktop.app import DesktopApp

    window = DesktopApp(db_path=str(tmp_path / "test.db"))
    pane_titles = [
        label for label in window.findChildren(QtWidgets.QLabel) if label.objectName() == "PaneTitleText"
    ]

    assert len(pane_titles) >= 2
    assert all(label.styleSheet() == "" for label in pane_titles)

    window.close()
