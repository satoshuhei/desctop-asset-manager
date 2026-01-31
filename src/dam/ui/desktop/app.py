from __future__ import annotations

import os
from typing import Callable, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from dam.core.domain.models import Configuration, Device, License
from dam.core.services.asset_service import AssetService
from dam.core.services.config_service import ConfigService
from dam.infra.db import init_db
from dam.infra.repositories import ConfigRepository, DeviceRepository, LicenseRepository


ASSET_MIME = "application/x-asset"


def _encode_drag(asset_type: str, asset_id: int, source_config_id: Optional[int]) -> bytes:
    if source_config_id is None:
        return f"{asset_type}:{asset_id}".encode("utf-8")
    return f"{asset_type}:{asset_id}:{source_config_id}".encode("utf-8")


def _decode_drag(data: bytes | QtCore.QByteArray) -> tuple[str, int, Optional[int]]:
    if isinstance(data, QtCore.QByteArray):
        data = bytes(data)
    parts = data.decode("utf-8").split(":")
    asset_type = parts[0]
    asset_id = int(parts[1])
    source_config_id = int(parts[2]) if len(parts) > 2 else None
    return asset_type, asset_id, source_config_id


class AssetListWidget(QtWidgets.QListWidget):
    def __init__(
        self,
        asset_type: str,
        allow_drop: bool = False,
        on_drop: Callable[[str, int, Optional[int]], None] | None = None,
        source_config_id: Optional[int] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.asset_type = asset_type
        self.on_drop = on_drop
        self.source_config_id = source_config_id

        self.setDragEnabled(True)
        self.setAcceptDrops(allow_drop)
        self.setDropIndicatorShown(allow_drop)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

    def startDrag(self, supportedActions: QtCore.Qt.DropActions) -> None:
        item = self.currentItem()
        if item is None:
            return
        asset_id = item.data(QtCore.Qt.UserRole)
        mime = QtCore.QMimeData()
        mime.setData(ASSET_MIME, _encode_drag(self.asset_type, asset_id, self.source_config_id))
        drag = QtGui.QDrag(self)
        drag.setMimeData(mime)
        drag.exec(QtCore.Qt.MoveAction)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if self.on_drop and event.mimeData().hasFormat(ASSET_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent) -> None:
        if self.on_drop and event.mimeData().hasFormat(ASSET_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        if not self.on_drop or not event.mimeData().hasFormat(ASSET_MIME):
            event.ignore()
            return
        asset_type, asset_id, source_config_id = _decode_drag(event.mimeData().data(ASSET_MIME))
        self.on_drop(asset_type, asset_id, source_config_id)
        event.acceptProposedAction()


class ConfigCardWidget(QtWidgets.QFrame):
    def __init__(
        self,
        config: Configuration,
        config_service: ConfigService,
        on_refresh: Callable[[], None],
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self._service = config_service
        self._on_refresh = on_refresh

        self.setObjectName("ConfigCard")
        self.setStyleSheet(
            "#ConfigCard { background-color: #111827; border: 1px solid #1f2937; border-radius: 14px; }"
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(10)

        header = QtWidgets.QHBoxLayout()
        self.title_edit = QtWidgets.QLineEdit(config.name)
        self.title_edit.setStyleSheet(
            "QLineEdit { color: #e5e7eb; font-size: 14px; font-weight: 600; border: none; }"
        )
        self.title_edit.editingFinished.connect(self._rename)
        header.addWidget(self.title_edit)
        layout.addLayout(header)

        device_label = QtWidgets.QLabel("Devices")
        device_label.setStyleSheet("color: #9ca3af; font-size: 11px;")
        layout.addWidget(device_label)

        self.device_list = AssetListWidget(
            "device",
            allow_drop=True,
            on_drop=self._handle_drop,
            source_config_id=config.config_id,
        )
        self.device_list.setStyleSheet(
            "QListWidget { background-color: #0b1220; color: #e5e7eb; border-radius: 10px; padding: 6px; }"
        )
        layout.addWidget(self.device_list)

        license_label = QtWidgets.QLabel("Licenses")
        license_label.setStyleSheet("color: #9ca3af; font-size: 11px;")
        layout.addWidget(license_label)

        self.license_list = AssetListWidget(
            "license",
            allow_drop=True,
            on_drop=self._handle_drop,
            source_config_id=config.config_id,
        )
        self.license_list.setStyleSheet(
            "QListWidget { background-color: #0b1220; color: #e5e7eb; border-radius: 10px; padding: 6px; }"
        )
        layout.addWidget(self.license_list)

        self.device_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.device_list.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(self.device_list, "device", pos)
        )
        self.license_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.license_list.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(self.license_list, "license", pos)
        )

    def refresh(self) -> None:
        self.device_list.clear()
        devices = self._service.list_config_devices(self.config.config_id)
        for device in devices:
            item = QtWidgets.QListWidgetItem(device.display_name or device.asset_no)
            item.setData(QtCore.Qt.UserRole, device.device_id)
            self.device_list.addItem(item)

        self.license_list.clear()
        licenses = self._service.list_config_licenses(self.config.config_id)
        for license_item in licenses:
            item = QtWidgets.QListWidgetItem(license_item.name)
            item.setData(QtCore.Qt.UserRole, license_item.license_id)
            self.license_list.addItem(item)

    def _rename(self) -> None:
        name = self.title_edit.text().strip()
        if not name:
            self.title_edit.setText(self.config.name)
            return
        if name != self.config.name:
            self._service.rename_config(self.config.config_id, name)
            self.config = Configuration(self.config.config_id, name, self.config.note)
            self._on_refresh()

    def _handle_drop(self, asset_type: str, asset_id: int, source_config_id: Optional[int]) -> None:
        if asset_type == "device":
            if source_config_id and source_config_id != self.config.config_id:
                self._service.move_device(source_config_id, self.config.config_id, asset_id)
            else:
                self._service.assign_device(self.config.config_id, asset_id)
        elif asset_type == "license":
            self._service.assign_license(self.config.config_id, asset_id)

        self._on_refresh()

    def _show_context_menu(self, list_widget: QtWidgets.QListWidget, asset_type: str, pos: QtCore.QPoint) -> None:
        item = list_widget.itemAt(pos)
        if item is None:
            return
        menu = QtWidgets.QMenu(self)
        remove_action = menu.addAction("Remove")
        action = menu.exec(list_widget.mapToGlobal(pos))
        if action != remove_action:
            return

        asset_id = item.data(QtCore.Qt.UserRole)
        if asset_type == "device":
            self._service.unassign_device(self.config.config_id, asset_id)
        else:
            self._service.unassign_license(self.config.config_id, asset_id)
        self._on_refresh()


class ConfigGraphicsView(QtWidgets.QGraphicsView):
    def __init__(self, scene: QtWidgets.QGraphicsScene, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(scene, parent)
        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        if event.modifiers() & QtCore.Qt.ControlModifier:
            zoom_factor = 1.1 if event.angleDelta().y() > 0 else 0.9
            self.scale(zoom_factor, zoom_factor)
        else:
            super().wheelEvent(event)


class ConfigCanvasWidget(QtWidgets.QWidget):
    def __init__(
        self,
        service: ConfigService,
        on_refresh_assets: Callable[[], None],
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._on_refresh_assets = on_refresh_assets
        self._cards: dict[int, ConfigCardWidget] = {}
        self._proxies: dict[int, QtWidgets.QGraphicsProxyWidget] = {}
        self._positions: dict[int, QtCore.QPointF] = {}

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QtWidgets.QHBoxLayout()
        toolbar.setContentsMargins(12, 12, 12, 8)
        title = QtWidgets.QLabel("Configuration Canvas")
        title.setStyleSheet("color: #e5e7eb; font-size: 14px; font-weight: 600;")
        toolbar.addWidget(title)
        toolbar.addStretch(1)

        add_button = QtWidgets.QPushButton("+ New Config")
        add_button.setObjectName("PrimaryButton")
        add_button.clicked.connect(self._add_config)
        toolbar.addWidget(add_button)
        layout.addLayout(toolbar)

        self.scene = QtWidgets.QGraphicsScene(self)
        self.view = ConfigGraphicsView(self.scene)
        self.view.setStyleSheet("background-color: #0b1020; border: none;")
        layout.addWidget(self.view)

        self.placeholder = QtWidgets.QGraphicsTextItem("Drop assets here")
        self.placeholder.setDefaultTextColor(QtGui.QColor("#4b5563"))
        self.placeholder.setFont(QtGui.QFont("Segoe UI", 18, QtGui.QFont.Bold))
        self.scene.addItem(self.placeholder)

    def refresh(self) -> None:
        for proxy in self._proxies.values():
            self.scene.removeItem(proxy)
        self._cards.clear()
        self._proxies.clear()

        configs = self._service.list_configs()
        for index, config in enumerate(configs):
            card = ConfigCardWidget(config, self._service, self._refresh_all)
            card.refresh()
            proxy = self.scene.addWidget(card)
            proxy.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
            proxy.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
            proxy.setCacheMode(QtWidgets.QGraphicsItem.DeviceCoordinateCache)

            pos = self._positions.get(config.config_id, self._default_position(index))
            proxy.setPos(pos)
            self._positions[config.config_id] = QtCore.QPointF(pos)

            self._cards[config.config_id] = card
            self._proxies[config.config_id] = proxy

        self._update_placeholder()

    def _refresh_all(self) -> None:
        for card in self._cards.values():
            card.refresh()
        self._on_refresh_assets()

    def _add_config(self) -> None:
        name, ok = QtWidgets.QInputDialog.getText(self, "New Configuration", "Configuration name")
        if not ok or not name.strip():
            return
        self._service.create_config(name=name.strip())
        self.refresh()
        self._animate_latest()

    def _animate_latest(self) -> None:
        if not self._proxies:
            return
        proxy = list(self._proxies.values())[-1]
        widget = proxy.widget()
        if widget is None:
            return
        effect = QtWidgets.QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        animation = QtCore.QPropertyAnimation(effect, b"opacity", widget)
        animation.setDuration(450)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

    def _default_position(self, index: int) -> QtCore.QPointF:
        col = index % 2
        row = index // 2
        x = 40 + col * 420
        y = 40 + row * 320
        return QtCore.QPointF(x, y)

    def _update_placeholder(self) -> None:
        if self._cards:
            self.placeholder.setVisible(False)
            return
        self.placeholder.setVisible(True)
        rect = self.view.viewport().rect()
        center = self.view.mapToScene(rect.center())
        bounds = self.placeholder.boundingRect()
        self.placeholder.setPos(center.x() - bounds.width() / 2, center.y() - bounds.height() / 2)


class AssetPaletteWidget(QtWidgets.QWidget):
    def __init__(self, service: AssetService, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._devices: list[Device] = []
        self._licenses: list[License] = []

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QtWidgets.QLabel("Asset Palette")
        header.setStyleSheet("color: #e5e7eb; font-size: 16px; font-weight: 700;")
        layout.addWidget(header)

        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Search assets")
        self.search.textChanged.connect(self._apply_filter)
        self.search.setStyleSheet(
            "QLineEdit { background-color: #111827; border-radius: 10px; padding: 8px; color: #e5e7eb; }"
        )
        layout.addWidget(self.search)

        device_label = QtWidgets.QLabel("Devices")
        device_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        layout.addWidget(device_label)
        self.device_list = AssetListWidget("device")
        self.device_list.setStyleSheet(
            "QListWidget { background-color: #0b1220; color: #e5e7eb; border-radius: 12px; padding: 6px; }"
        )
        layout.addWidget(self.device_list, 1)

        license_label = QtWidgets.QLabel("Licenses")
        license_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        layout.addWidget(license_label)
        self.license_list = AssetListWidget("license")
        self.license_list.setStyleSheet(
            "QListWidget { background-color: #0b1220; color: #e5e7eb; border-radius: 12px; padding: 6px; }"
        )
        layout.addWidget(self.license_list, 1)

    def refresh(self) -> None:
        self._devices = self._service.list_devices()
        self._licenses = self._service.list_licenses()
        self._apply_filter(self.search.text())

    def _apply_filter(self, keyword: str) -> None:
        keyword = keyword.lower().strip()

        self.device_list.clear()
        for device in self._devices:
            label = device.display_name or device.asset_no
            if not keyword or keyword in label.lower():
                item = QtWidgets.QListWidgetItem(label)
                item.setData(QtCore.Qt.UserRole, device.device_id)
                self.device_list.addItem(item)

        self.license_list.clear()
        for license_item in self._licenses:
            label = license_item.name
            if not keyword or keyword in label.lower():
                item = QtWidgets.QListWidgetItem(label)
                item.setData(QtCore.Qt.UserRole, license_item.license_id)
                self.license_list.addItem(item)


class DesktopApp(QtWidgets.QMainWindow):
    def __init__(self, db_path: Optional[str] = None) -> None:
        super().__init__()
        self.setWindowTitle("Desktop Asset Manager")
        self.resize(1280, 720)

        if db_path is None:
            db_path = os.path.join(os.getcwd(), "dam.db")
        conn = init_db(db_path)

        device_repo = DeviceRepository(conn)
        license_repo = LicenseRepository(conn)
        config_repo = ConfigRepository(conn)

        self.asset_service = AssetService(device_repo, license_repo)
        self.config_service = ConfigService(config_repo)

        self._apply_theme()

        splitter = QtWidgets.QSplitter()
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("QSplitter::handle { background-color: #1f2937; }")

        self.asset_palette = AssetPaletteWidget(self.asset_service)
        self.canvas = ConfigCanvasWidget(self.config_service, self._refresh_assets)

        splitter.addWidget(self.asset_palette)
        splitter.addWidget(self.canvas)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        self.setCentralWidget(splitter)

        self._refresh_assets()
        self.canvas.refresh()

    def _refresh_assets(self) -> None:
        self.asset_palette.refresh()

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow { background-color: #0b1020; }
            QWidget { font-family: Segoe UI; }
            QPushButton#PrimaryButton {
                background-color: #2563eb;
                color: white;
                border-radius: 10px;
                padding: 8px 14px;
                font-weight: 600;
            }
            QPushButton#PrimaryButton:hover { background-color: #1d4ed8; }
            """
        )


def run_app() -> None:
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    window = DesktopApp()
    window.show()
    app.exec()
