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
    from dam.ui.i18n import tr

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
    from dam.ui.i18n import tr

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
    widget._arrange_cards("row", sort_key="config_no_asc")

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

    log_text = widget.log_panel._view.toPlainText()
    assert tr("Arranged") in log_text

    widget.deleteLater()
    app.processEvents()


def test_config_canvas_arrange_sorts_by_dates(tmp_path: Path) -> None:
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
    config_repo = ConfigRepository(conn)
    config_service = ConfigService(config_repo)

    config_a = config_service.create_config(name="Config A", config_no="CNFG-001")
    config_b = config_service.create_config(name="Config B", config_no="CNFG-002")
    config_c = config_service.create_config(name="Config C", config_no="CNFG-003")

    conn.execute(
        "UPDATE configurations SET created_at = ?, updated_at = ? WHERE config_id = ?",
        ("2024-01-01 10:00:00", "2024-02-01 10:00:00", config_a.config_id),
    )
    conn.execute(
        "UPDATE configurations SET created_at = ?, updated_at = ? WHERE config_id = ?",
        ("2024-01-03 10:00:00", "2024-02-03 10:00:00", config_b.config_id),
    )
    conn.execute(
        "UPDATE configurations SET created_at = ?, updated_at = ? WHERE config_id = ?",
        ("2024-01-02 10:00:00", "2024-02-02 10:00:00", config_c.config_id),
    )
    conn.commit()

    widget = ConfigCanvasWidget(config_service, on_refresh_assets=lambda: asset_service.list_devices())
    widget.resize(1200, 800)
    widget.show()
    app.processEvents()

    widget.refresh()
    widget._arrange_cards("row", sort_key="updated_desc")
    positions = {
        config_a.config_id: widget._proxies[config_a.config_id].pos(),
        config_b.config_id: widget._proxies[config_b.config_id].pos(),
        config_c.config_id: widget._proxies[config_c.config_id].pos(),
    }
    ordered_ids = [
        item[0]
        for item in sorted(positions.items(), key=lambda item: (item[1].y(), item[1].x()))
    ]
    assert ordered_ids == [config_b.config_id, config_c.config_id, config_a.config_id]

    widget._arrange_cards("row", sort_key="created_desc")
    positions = {
        config_a.config_id: widget._proxies[config_a.config_id].pos(),
        config_b.config_id: widget._proxies[config_b.config_id].pos(),
        config_c.config_id: widget._proxies[config_c.config_id].pos(),
    }
    ordered_ids = [
        item[0]
        for item in sorted(positions.items(), key=lambda item: (item[1].y(), item[1].x()))
    ]
    assert ordered_ids == [config_b.config_id, config_c.config_id, config_a.config_id]

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


def test_device_panel_filters_by_status(tmp_path: Path) -> None:
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets

    from dam.core.services.asset_service import AssetService
    from dam.infra.db import init_db
    from dam.infra.repositories import DeviceRepository, LicenseRepository
    from dam.ui.desktop.app import DevicePanel
    from dam.ui.i18n import state_display

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    conn = init_db(":memory:")
    asset_service = AssetService(DeviceRepository(conn), LicenseRepository(conn))
    asset_service.add_device(
        asset_no="DEV-999",
        display_name="Retired",
        device_type="PC",
        model="Model Z",
        version="v1",
        state="retired",
        note="test",
    )

    panel = DevicePanel(asset_service, toast=None)
    panel.refresh()
    panel.status_filter.setCurrentText(state_display("DeviceState", "retired"))
    panel._apply_filter(panel.search.text())

    assert panel.device_table.rowCount() >= 1

    panel.deleteLater()
    app.processEvents()


def test_device_type_filter_reset_returns_results(tmp_path: Path) -> None:
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets

    from dam.core.services.asset_service import AssetService
    from dam.infra.db import init_db
    from dam.infra.repositories import DeviceRepository, LicenseRepository
    from dam.ui.desktop.app import DevicePanel
    from dam.ui.i18n import tr

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    conn = init_db(":memory:")
    asset_service = AssetService(DeviceRepository(conn), LicenseRepository(conn))

    panel = DevicePanel(asset_service, toast=None)
    panel.refresh()
    if panel.type_filter.count() > 1:
        panel.type_filter.setCurrentIndex(1)
    panel.type_filter.setCurrentText(tr("All"))
    panel._apply_filter(None)

    assert panel.device_table.rowCount() > 0

    panel.deleteLater()
    app.processEvents()


def test_device_table_defaults_to_no_desc(tmp_path: Path) -> None:
    pytest.importorskip("PySide6")
    from PySide6 import QtCore, QtWidgets

    from dam.core.services.asset_service import AssetService
    from dam.infra.db import init_db
    from dam.infra.repositories import DeviceRepository, LicenseRepository
    from dam.ui.desktop.app import DevicePanel

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    conn = init_db(":memory:")
    asset_service = AssetService(DeviceRepository(conn), LicenseRepository(conn))
    panel = DevicePanel(asset_service, toast=None)
    panel.refresh()

    header = panel.device_table.horizontalHeader()
    assert header.sortIndicatorSection() == 0
    assert header.sortIndicatorOrder() == QtCore.Qt.SortOrder.DescendingOrder

    panel.deleteLater()
    app.processEvents()


def test_license_panel_filters_by_status(tmp_path: Path) -> None:
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets

    from dam.core.services.asset_service import AssetService
    from dam.infra.db import init_db
    from dam.infra.repositories import DeviceRepository, LicenseRepository
    from dam.ui.desktop.app import LicensePanel
    from dam.ui.i18n import state_display

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    conn = init_db(":memory:")
    asset_service = AssetService(DeviceRepository(conn), LicenseRepository(conn))
    asset_service.add_license(
        license_no="LIC-999",
        name="Expired",
        license_key="LIC-999",
        state="expired",
        note="test",
    )

    panel = LicensePanel(asset_service, toast=None)
    panel.refresh()
    panel.status_filter.setCurrentText(state_display("LicenseState", "expired"))
    panel._apply_filter(panel.search.text())

    assert panel.license_table.rowCount() >= 1

    panel.deleteLater()
    app.processEvents()


def test_license_table_defaults_to_no_desc(tmp_path: Path) -> None:
    pytest.importorskip("PySide6")
    from PySide6 import QtCore, QtWidgets

    from dam.core.services.asset_service import AssetService
    from dam.infra.db import init_db
    from dam.infra.repositories import DeviceRepository, LicenseRepository
    from dam.ui.desktop.app import LicensePanel

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    conn = init_db(":memory:")
    asset_service = AssetService(DeviceRepository(conn), LicenseRepository(conn))
    panel = LicensePanel(asset_service, toast=None)
    panel.refresh()

    header = panel.license_table.horizontalHeader()
    assert header.sortIndicatorSection() == 0
    assert header.sortIndicatorOrder() == QtCore.Qt.SortOrder.DescendingOrder

    panel.deleteLater()
    app.processEvents()


def test_config_card_hides_device_headers(tmp_path: Path) -> None:
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

    config = config_service.create_config(name="Config A")
    widget = ConfigCanvasWidget(config_service, on_refresh_assets=lambda: asset_service.list_devices())
    widget.refresh()

    card = widget._cards[config.config_id]
    assert not card.device_list.horizontalHeader().isVisible()

    widget.deleteLater()
    app.processEvents()


def test_config_card_click_selects_proxy(tmp_path: Path) -> None:
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

    config = config_service.create_config(name="Config A")
    config_b = config_service.create_config(name="Config B")
    widget = ConfigCanvasWidget(config_service, on_refresh_assets=lambda: asset_service.list_devices())
    widget.refresh()

    proxy = widget._proxies[config.config_id]
    proxy.setSelected(False)

    other_proxy = widget._proxies[config_b.config_id]
    other_proxy.setSelected(True)

    card = widget._cards[config.config_id]
    card._ensure_selected()

    assert proxy.isSelected()
    assert not other_proxy.isSelected()

    widget.deleteLater()
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
    assert tr("Created At") in labels
    assert tr("Updated At") in labels

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
    assert "color: #ffffff" in style
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
    assert all("color: #ffffff" in label.styleSheet() for label in pane_titles)

    window.close()


def test_pane_area_styling_is_present(tmp_path: Path) -> None:
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    from dam.ui.desktop.app import DesktopApp

    window = DesktopApp(db_path=str(tmp_path / "test.db"))
    style = window.styleSheet()

    assert "QWidget#PaneArea" in style

    window.close()


def test_log_panel_appends_messages(tmp_path: Path) -> None:
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
    widget.log_message("Test log entry")

    log_text = widget.log_panel._view.toPlainText()
    assert "Test log entry" in log_text

    widget.deleteLater()
    app.processEvents()


def test_config_card_rename_preserves_timestamps(tmp_path: Path) -> None:
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets

    from dam.core.services.config_service import ConfigService
    from dam.infra.db import init_db
    from dam.infra.repositories import ConfigRepository
    from dam.ui.desktop.app import BasicActions, ConfigCardWidget

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    conn = init_db(":memory:")
    config_service = ConfigService(ConfigRepository(conn))
    config = config_service.create_config(name="Config A")

    actions = BasicActions(config_service, refresh_all=lambda: None)
    card = ConfigCardWidget(
        config,
        config_service,
        actions,
        on_refresh=lambda: None,
        on_hide=lambda _cid: None,
        on_drag_start=lambda _cid, _pos: None,
        on_drag_move=lambda _pos: None,
        on_drag_end=lambda _pos: None,
        on_log=lambda _message: None,
    )

    card.title_edit.setText("Config A1")
    card._rename()

    assert card.config.name == "Config A1"
    assert card.config.created_at
    assert card.config.updated_at

    card.deleteLater()
    app.processEvents()
