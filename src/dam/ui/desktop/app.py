from __future__ import annotations

import os
import re
from typing import Callable, Dict, List, Optional, Tuple

from PySide6 import QtCore, QtGui, QtWidgets

from dam.core.domain.models import Configuration, Device, License
from dam.core.services.asset_service import AssetService
from dam.core.services.config_service import ConfigService
from dam.infra.db import init_db
from dam.infra.repositories import ConfigRepository, DeviceRepository, LicenseRepository
from dam.ui.i18n import state_display, state_to_physical, states_display, tr
from dam.ui.ui_state import CanvasState, UIStateStore, ui_state_db_path


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


def _build_pane_title(text: str) -> QtWidgets.QFrame:
    frame = QtWidgets.QFrame()
    frame.setObjectName("PaneTitleBar")
    frame.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
    layout = QtWidgets.QHBoxLayout(frame)
    layout.setContentsMargins(10, 6, 10, 6)
    label = QtWidgets.QLabel(text)
    label.setObjectName("PaneTitleText")
    label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
    layout.addWidget(label)
    layout.addStretch(1)
    return frame


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


class AssetTableWidget(QtWidgets.QTableWidget):
    def __init__(
        self,
        asset_type: str,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.asset_type = asset_type
        self.setDragEnabled(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setShowGrid(True)
        self.setGridStyle(QtCore.Qt.SolidLine)
        self.verticalHeader().setDefaultSectionSize(28)

    def startDrag(self, supportedActions: QtCore.Qt.DropActions) -> None:
        row = self.currentRow()
        if row < 0:
            return
        asset_id_item = self.item(row, 0)
        if asset_id_item is None:
            return
        asset_id = asset_id_item.data(QtCore.Qt.UserRole)
        mime = QtCore.QMimeData()
        mime.setData(ASSET_MIME, _encode_drag(self.asset_type, asset_id, None))
        drag = QtGui.QDrag(self)
        drag.setMimeData(mime)
        drag.exec(QtCore.Qt.MoveAction)


class ConfigAssetTableWidget(QtWidgets.QTableWidget):
    def __init__(
        self,
        asset_type: str,
        on_drop: Callable[[str, int, Optional[int]], None],
        source_config_id: Optional[int],
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.asset_type = asset_type
        self.on_drop = on_drop
        self.source_config_id = source_config_id
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setShowGrid(True)
        self.setGridStyle(QtCore.Qt.SolidLine)
        self.verticalHeader().setDefaultSectionSize(26)

    def startDrag(self, supportedActions: QtCore.Qt.DropActions) -> None:
        row = self.currentRow()
        if row < 0:
            return
        asset_item = self.item(row, 0)
        if asset_item is None:
            return
        asset_id = asset_item.data(QtCore.Qt.UserRole)
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


class DragHandleLabel(QtWidgets.QLabel):
    def __init__(
        self,
        on_start: Callable[[QtCore.QPoint], None],
        on_move: Callable[[QtCore.QPoint], None],
        on_end: Callable[[QtCore.QPoint], None],
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__("⠿", parent)
        self._on_start = on_start
        self._on_move = on_move
        self._on_end = on_end
        self.setCursor(QtCore.Qt.OpenHandCursor)
        self.setToolTip(tr("Move"))

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.setCursor(QtCore.Qt.ClosedHandCursor)
            self._on_start(event.globalPosition().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.buttons() & QtCore.Qt.LeftButton:
            self._on_move(event.globalPosition().toPoint())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.setCursor(QtCore.Qt.OpenHandCursor)
            self._on_end(event.globalPosition().toPoint())
            event.accept()
            return
        super().mouseReleaseEvent(event)


class UndoStack:
    def __init__(self) -> None:
        self._undos: List[tuple[str, Callable[[], None], Callable[[], None]]] = []
        self._redos: List[tuple[str, Callable[[], None], Callable[[], None]]] = []

    def push(
        self,
        label: str,
        do_fn: Callable[[], None],
        undo_fn: Callable[[], None],
        execute: bool = True,
    ) -> None:
        if execute:
            do_fn()
        self._undos.append((label, do_fn, undo_fn))
        self._redos.clear()

    def undo(self) -> None:
        if not self._undos:
            return
        label, do_fn, undo_fn = self._undos.pop()
        undo_fn()
        self._redos.append((label, do_fn, undo_fn))

    def redo(self) -> None:
        if not self._redos:
            return
        label, do_fn, undo_fn = self._redos.pop()
        do_fn()
        self._undos.append((label, do_fn, undo_fn))


class ToastManager(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.addStretch(1)
        self._layout = layout

    def show_message(self, message: str) -> None:
        frame = QtWidgets.QFrame(self)
        frame.setStyleSheet(
            "QFrame { background-color: #f8f8f8; border: 1px solid #d5d5d5; "
            "border-radius: 8px; }"
        )
        label = QtWidgets.QLabel(message, frame)
        label.setStyleSheet("color: #333333; font-size: 12px; padding: 8px 12px;")
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label)
        self._layout.insertWidget(self._layout.count() - 1, frame, 0, QtCore.Qt.AlignRight)
        QtCore.QTimer.singleShot(2400, lambda: self._remove_toast(frame))

    def _remove_toast(self, frame: QtWidgets.QFrame) -> None:
        frame.setParent(None)
        frame.deleteLater()


class UIActions:
    def __init__(
        self,
        asset_service: AssetService,
        config_service: ConfigService,
        refresh_all: Callable[[], None],
        toast: ToastManager,
        undo_stack: UndoStack,
    ) -> None:
        self._asset_service = asset_service
        self._config_service = config_service
        self._refresh_all = refresh_all
        self._toast = toast
        self._undo_stack = undo_stack

    def _find_license_owner(self, license_id: int) -> Optional[int]:
        for config in self._config_service.list_configs():
            licenses = self._config_service.list_config_licenses(config.config_id)
            if any(item.license_id == license_id for item in licenses):
                return config.config_id
        return None

    def assign_device(self, config_id: int, device_id: int, source_config_id: Optional[int]) -> None:
        if source_config_id and source_config_id != config_id:
            label = tr("Devices")

            def do_fn() -> None:
                self._config_service.move_device(source_config_id, config_id, device_id)
                self._refresh_all()
                self._toast.show_message(tr("Device moved"))

            def undo_fn() -> None:
                self._config_service.move_device(config_id, source_config_id, device_id)
                self._refresh_all()
                self._toast.show_message(tr("Undo"))

            self._undo_stack.push(label, do_fn, undo_fn)
            return

        def do_assign() -> None:
            self._config_service.assign_device(config_id, device_id)
            self._refresh_all()
            self._toast.show_message(tr("Device assigned"))

        def undo_assign() -> None:
            self._config_service.unassign_device(config_id, device_id)
            self._refresh_all()
            self._toast.show_message(tr("Undo"))

        self._undo_stack.push(tr("Devices"), do_assign, undo_assign)

    def assign_license(self, config_id: int, license_id: int) -> None:
        previous_owner = self._find_license_owner(license_id)

        def do_fn() -> None:
            self._config_service.assign_license(config_id, license_id)
            self._refresh_all()
            self._toast.show_message(tr("License assigned"))

        def undo_fn() -> None:
            if previous_owner is None:
                self._config_service.unassign_license(config_id, license_id)
            else:
                self._config_service.assign_license(previous_owner, license_id)
            self._refresh_all()
            self._toast.show_message(tr("Undo"))

        self._undo_stack.push(tr("Licenses"), do_fn, undo_fn)

    def unassign_device(self, config_id: int, device_id: int) -> None:
        def do_fn() -> None:
            self._config_service.unassign_device(config_id, device_id)
            self._refresh_all()
            self._toast.show_message(tr("Device unassigned"))

        def undo_fn() -> None:
            self._config_service.assign_device(config_id, device_id)
            self._refresh_all()
            self._toast.show_message(tr("Undo"))

        self._undo_stack.push(tr("Devices"), do_fn, undo_fn)

    def unassign_license(self, config_id: int, license_id: int) -> None:
        def do_fn() -> None:
            self._config_service.unassign_license(config_id, license_id)
            self._refresh_all()
            self._toast.show_message(tr("License unassigned"))

        def undo_fn() -> None:
            self._config_service.assign_license(config_id, license_id)
            self._refresh_all()
            self._toast.show_message(tr("Undo"))

        self._undo_stack.push(tr("Licenses"), do_fn, undo_fn)

    def rename_config(self, config_id: int, old_name: str, new_name: str) -> None:
        if old_name == new_name:
            return

        def do_fn() -> None:
            self._config_service.rename_config(config_id, new_name)
            self._refresh_all()
            self._toast.show_message(tr("Config renamed"))

        def undo_fn() -> None:
            self._config_service.rename_config(config_id, old_name)
            self._refresh_all()
            self._toast.show_message(tr("Undo"))

        self._undo_stack.push(tr("Configuration"), do_fn, undo_fn)


class BasicActions:
    def __init__(self, config_service: ConfigService, refresh_all: Callable[[], None]) -> None:
        self._config_service = config_service
        self._refresh_all = refresh_all

    def assign_device(self, config_id: int, device_id: int, source_config_id: Optional[int]) -> None:
        if source_config_id and source_config_id != config_id:
            self._config_service.move_device(source_config_id, config_id, device_id)
        else:
            self._config_service.assign_device(config_id, device_id)
        self._refresh_all()

    def assign_license(self, config_id: int, license_id: int) -> None:
        self._config_service.assign_license(config_id, license_id)
        self._refresh_all()

    def unassign_device(self, config_id: int, device_id: int) -> None:
        self._config_service.unassign_device(config_id, device_id)
        self._refresh_all()

    def unassign_license(self, config_id: int, license_id: int) -> None:
        self._config_service.unassign_license(config_id, license_id)
        self._refresh_all()

    def rename_config(self, config_id: int, old_name: str, new_name: str) -> None:
        if old_name != new_name:
            self._config_service.rename_config(config_id, new_name)
            self._refresh_all()


class ConfigCardWidget(QtWidgets.QFrame):
    def __init__(
        self,
        config: Configuration,
        config_service: ConfigService,
        actions: UIActions,
        on_refresh: Callable[[], None],
        on_hide: Callable[[int], None],
        on_drag_start: Callable[[int, QtCore.QPoint], None],
        on_drag_move: Callable[[QtCore.QPoint], None],
        on_drag_end: Callable[[QtCore.QPoint], None],
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self._service = config_service
        self._actions = actions
        self._on_refresh = on_refresh
        self._on_hide = on_hide
        self._on_drag_start = on_drag_start
        self._on_drag_move = on_drag_move
        self._on_drag_end = on_drag_end

        self.setObjectName("ConfigCard")
        self.setStyleSheet(
            "#ConfigCard { background-color: #ffffff; border: 1px solid #d5d5d5; border-radius: 10px; }"
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(10)

        header = QtWidgets.QHBoxLayout()
        handle = DragHandleLabel(
            lambda pos: self._on_drag_start(self.config.config_id, pos),
            self._on_drag_move,
            self._on_drag_end,
        )
        handle.setStyleSheet("color: #777777; font-size: 14px; padding: 2px 4px;")
        header.addWidget(handle)
        config_no_label = QtWidgets.QLabel(self.config.config_no)
        config_no_label.setStyleSheet("color: #555555; font-size: 12px; font-weight: 600;")
        header.addWidget(config_no_label)
        self.title_edit = QtWidgets.QLineEdit(config.name)
        self.title_edit.setStyleSheet(
            "QLineEdit { background-color: #ffffff; color: #333333; font-size: 14px; font-weight: 600; "
            "border: 1px solid #cfcfcf; border-radius: 6px; padding: 4px 8px; }"
        )
        self.title_edit.editingFinished.connect(self._rename)
        header.addWidget(self.title_edit)
        layout.addLayout(header)

        device_label = QtWidgets.QLabel(tr("Devices"))
        device_label.setStyleSheet("color: #666666; font-size: 11px;")
        layout.addWidget(device_label)

        self.device_list = ConfigAssetTableWidget(
            "device",
            on_drop=self._handle_drop,
            source_config_id=config.config_id,
        )
        self.device_list.setColumnCount(4)
        self.device_list.setHorizontalHeaderLabels(
            [tr("Asset No"), tr("Display Name"), tr("Model"), tr("Version")]
        )
        self.device_list.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        self.device_list.setStyleSheet(
            "QTableWidget { background-color: #ffffff; color: #333333; border-radius: 6px; padding: 6px; "
            "border: 1px solid #d5d5d5; gridline-color: #e3e3e3; }"
            "QHeaderView::section { background-color: #e6e6e6; color: #333333; padding: 4px; border: none; "
            "font-weight: 600; }"
            "QTableWidget::item:selected { background-color: #dbe8f6; color: #333333; }"
        )
        header_view = self.device_list.horizontalHeader()
        header_view.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header_view.setStretchLastSection(True)
        layout.addWidget(self.device_list)

        license_label = QtWidgets.QLabel(tr("Licenses"))
        license_label.setStyleSheet("color: #666666; font-size: 11px;")
        layout.addWidget(license_label)

        self.license_list = AssetListWidget(
            "license",
            allow_drop=True,
            on_drop=self._handle_drop,
            source_config_id=config.config_id,
        )
        self.license_list.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        self.license_list.setStyleSheet(
            "QListWidget { background-color: #ffffff; color: #333333; border-radius: 6px; padding: 6px; "
            "border: 1px solid #d5d5d5; }"
            "QListWidget::item:selected { background-color: #dbe8f6; color: #333333; }"
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

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_card_menu)

    def refresh(self) -> None:
        self.device_list.setRowCount(0)
        devices = self._service.list_config_devices(self.config.config_id)
        for device in devices:
            row = self.device_list.rowCount()
            self.device_list.insertRow(row)
            asset_item = QtWidgets.QTableWidgetItem(device.asset_no)
            asset_item.setData(QtCore.Qt.UserRole, device.device_id)
            self.device_list.setItem(row, 0, asset_item)
            self.device_list.setItem(row, 1, QtWidgets.QTableWidgetItem(device.display_name or ""))
            self.device_list.setItem(row, 2, QtWidgets.QTableWidgetItem(device.model))
            self.device_list.setItem(row, 3, QtWidgets.QTableWidgetItem(device.version))

        self.device_list.resizeColumnsToContents()
        self._adjust_table_height(self.device_list)

        self.license_list.clear()
        licenses = self._service.list_config_licenses(self.config.config_id)
        for license_item in licenses:
            item = QtWidgets.QListWidgetItem(license_item.name)
            item.setData(QtCore.Qt.UserRole, license_item.license_id)
            self.license_list.addItem(item)

        self._adjust_list_height(self.license_list)

    def _adjust_list_height(self, list_widget: QtWidgets.QListWidget) -> None:
        count = list_widget.count()
        if count == 0:
            list_widget.setFixedHeight(48)
            return
        row_height = list_widget.sizeHintForRow(0)
        spacing = list_widget.spacing()
        frame = list_widget.frameWidth() * 2
        height = (row_height + spacing) * count + frame + 8
        list_widget.setFixedHeight(min(height, 220))

    def _adjust_table_height(self, table: QtWidgets.QTableWidget) -> None:
        rows = table.rowCount()
        if rows == 0:
            table.setFixedHeight(56)
            return
        row_height = table.verticalHeader().defaultSectionSize()
        header_height = table.horizontalHeader().height()
        frame = table.frameWidth() * 2
        height = header_height + row_height * rows + frame + 6
        table.setFixedHeight(min(height, 240))

    def _rename(self) -> None:
        name = self.title_edit.text().strip()
        if not name:
            self.title_edit.setText(self.config.name)
            return
        if name != self.config.name:
            self._actions.rename_config(self.config.config_id, self.config.name, name)
            self.config = Configuration(self.config.config_id, self.config.config_no, name, self.config.note)
            self._on_refresh()

    def _handle_drop(self, asset_type: str, asset_id: int, source_config_id: Optional[int]) -> None:
        if asset_type == "device":
            self._actions.assign_device(self.config.config_id, asset_id, source_config_id)
        elif asset_type == "license":
            self._actions.assign_license(self.config.config_id, asset_id)

        self._on_refresh()

    def _show_context_menu(self, list_widget: QtWidgets.QWidget, asset_type: str, pos: QtCore.QPoint) -> None:
        item = list_widget.itemAt(pos)
        if item is None:
            return
        menu = QtWidgets.QMenu(self)
        remove_action = menu.addAction(tr("Remove"))
        action = menu.exec(list_widget.mapToGlobal(pos))
        if action != remove_action:
            return

        if isinstance(list_widget, QtWidgets.QTableWidget):
            row = item.row()
            asset_item = list_widget.item(row, 0)
            if asset_item is None:
                return
            asset_id = asset_item.data(QtCore.Qt.UserRole)
        else:
            asset_id = item.data(QtCore.Qt.UserRole)
        if asset_type == "device":
            self._actions.unassign_device(self.config.config_id, asset_id)
        else:
            self._actions.unassign_license(self.config.config_id, asset_id)
        self._on_refresh()

    def _show_card_menu(self, pos: QtCore.QPoint) -> None:
        menu = QtWidgets.QMenu(self)
        rename_action = menu.addAction(tr("Rename"))
        delete_action = menu.addAction(tr("Delete"))
        action = menu.exec(self.mapToGlobal(pos))
        if action == rename_action:
            self.title_edit.setFocus()
            self.title_edit.selectAll()
        elif action == delete_action:
            self._on_hide(self.config.config_id)


class ConfigGraphicsView(QtWidgets.QGraphicsView):
    viewChanged = QtCore.Signal()

    def __init__(self, scene: QtWidgets.QGraphicsScene, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(scene, parent)
        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self._space_pressed = False

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        if event.modifiers() & QtCore.Qt.ControlModifier:
            zoom_factor = 1.1 if event.angleDelta().y() > 0 else 0.9
            self.scale(zoom_factor, zoom_factor)
            self.viewChanged.emit()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == QtCore.Qt.Key_Space:
            self._space_pressed = True
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self.setCursor(QtCore.Qt.OpenHandCursor)
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == QtCore.Qt.Key_Space:
            self._space_pressed = False
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
            self.setCursor(QtCore.Qt.ArrowCursor)
            event.accept()
            return
        super().keyReleaseEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        if self._space_pressed:
            self.viewChanged.emit()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        self.viewChanged.emit()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self.viewChanged.emit()


class ConfigCardProxy(QtWidgets.QGraphicsProxyWidget):
    GRID_SIZE = 20

    def __init__(self, config_id: int, on_moved: Callable[[int, QtCore.QPointF, QtCore.QPointF], None]) -> None:
        super().__init__()
        self._config_id = config_id
        self._on_moved = on_moved
        self._drag_start = QtCore.QPointF(0, 0)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self.setSelected(True)
        self._drag_start = QtCore.QPointF(self.pos())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        snapped = self._snap(self.pos())
        if snapped != self.pos():
            self.setPos(snapped)
        if snapped != self._drag_start:
            self._on_moved(self._config_id, self._drag_start, snapped)

    @classmethod
    def _snap(cls, pos: QtCore.QPointF) -> QtCore.QPointF:
        x = round(pos.x() / cls.GRID_SIZE) * cls.GRID_SIZE
        y = round(pos.y() / cls.GRID_SIZE) * cls.GRID_SIZE
        return QtCore.QPointF(x, y)


class MiniMapView(QtWidgets.QGraphicsView):
    def __init__(self, scene: QtWidgets.QGraphicsScene, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(scene, parent)
        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setInteractive(False)
        self.setStyleSheet("background-color: rgba(15, 23, 42, 200); border: 1px solid #334155; border-radius: 8px;")
        self._view_rect = self.scene().addRect(QtCore.QRectF(), QtGui.QPen(QtGui.QColor("#38bdf8"), 1.5))

    def update_view_rect(self, rect: QtCore.QRectF) -> None:
        self._view_rect.setRect(rect)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        scene_pos = self.mapToScene(event.pos())
        self.parent().center_on(scene_pos)


class ConfigCanvasWidget(QtWidgets.QWidget):
    GRID_SIZE = 20

    def __init__(
        self,
        service: ConfigService,
        on_refresh_assets: Callable[[], None],
        db_path: str = ":memory:",
        actions: UIActions | None = None,
        undo_stack: UndoStack | None = None,
        toast: ToastManager | None = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._on_refresh_assets = on_refresh_assets
        self._actions = actions
        self._undo_stack = undo_stack
        self._toast = toast
        self._state_store = UIStateStore(ui_state_db_path(db_path))
        self._cards: dict[int, ConfigCardWidget] = {}
        self._proxies: dict[int, ConfigCardProxy] = {}
        self._positions: dict[int, QtCore.QPointF] = {}
        self._hidden: dict[int, bool] = {}
        self._dragging_id: Optional[int] = None
        self._drag_offset = QtCore.QPointF(0, 0)
        self._drag_start_pos = QtCore.QPointF(0, 0)
        self._selected_config_id: Optional[int] = None

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("QSplitter::handle { background-color: #d5d5d5; }")

        detail_panel = QtWidgets.QFrame()
        detail_panel.setStyleSheet(
            "QFrame { background-color: #f8f8f8; border-bottom: 1px solid #d5d5d5; }"
            "QLabel { color: #333333; }"
        )
        detail_layout = QtWidgets.QGridLayout(detail_panel)
        detail_layout.setContentsMargins(12, 10, 12, 10)
        detail_layout.setHorizontalSpacing(10)
        detail_layout.setVerticalSpacing(6)

        detail_title = _build_pane_title(tr("Configuration Details"))
        detail_layout.addWidget(detail_title, 0, 0, 1, 6)

        detail_layout.addWidget(QtWidgets.QLabel(tr("Config No")), 1, 0)
        self.detail_no = QtWidgets.QLineEdit()
        self.detail_no.setReadOnly(True)
        detail_layout.addWidget(self.detail_no, 1, 1)

        detail_layout.addWidget(QtWidgets.QLabel(tr("Configuration name")), 1, 2)
        self.detail_name = QtWidgets.QLineEdit()
        self.detail_name.setReadOnly(True)
        detail_layout.addWidget(self.detail_name, 1, 3)

        detail_layout.setColumnStretch(3, 1)

        devices_title = QtWidgets.QLabel(tr("Devices"))
        devices_title.setObjectName("PaneSectionTitle")
        detail_layout.addWidget(devices_title, 2, 0, 1, 1)
        self.detail_devices = QtWidgets.QTableWidget()
        self.detail_devices.setColumnCount(5)
        self.detail_devices.setHorizontalHeaderLabels(
            [tr("Asset No"), tr("Type"), tr("Display Name"), tr("Model"), tr("Version")]
        )
        self.detail_devices.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.detail_devices.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.detail_devices.verticalHeader().setVisible(False)
        self.detail_devices.setAlternatingRowColors(True)
        self.detail_devices.verticalHeader().setDefaultSectionSize(26)
        devices_header = self.detail_devices.horizontalHeader()
        devices_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        devices_header.setStretchLastSection(True)
        self.detail_devices.setStyleSheet(
            "QTableWidget { background-color: #ffffff; color: #333333; border-radius: 6px; border: 1px solid #d5d5d5; }"
            "QHeaderView::section { background-color: #f0f0f0; color: #333333; padding: 4px; border: none; }"
        )
        detail_layout.addWidget(self.detail_devices, 2, 1, 1, 5)

        licenses_title = QtWidgets.QLabel(tr("Licenses"))
        licenses_title.setObjectName("PaneSectionTitle")
        detail_layout.addWidget(licenses_title, 3, 0, 1, 1)
        self.detail_licenses = QtWidgets.QTableWidget()
        self.detail_licenses.setColumnCount(3)
        self.detail_licenses.setHorizontalHeaderLabels([tr("Subject"), tr("License Key"), tr("Status")])
        self.detail_licenses.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.detail_licenses.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.detail_licenses.verticalHeader().setVisible(False)
        self.detail_licenses.setAlternatingRowColors(True)
        self.detail_licenses.verticalHeader().setDefaultSectionSize(26)
        licenses_header = self.detail_licenses.horizontalHeader()
        licenses_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        licenses_header.setStretchLastSection(True)
        self.detail_licenses.setStyleSheet(
            "QTableWidget { background-color: #ffffff; color: #333333; border-radius: 6px; border: 1px solid #d5d5d5; }"
            "QHeaderView::section { background-color: #f0f0f0; color: #333333; padding: 4px; border: none; }"
        )
        detail_layout.addWidget(self.detail_licenses, 3, 1, 1, 5)

        detail_layout.setColumnStretch(3, 1)
        splitter.addWidget(detail_panel)

        self._canvas_container = QtWidgets.QWidget()
        canvas_layout = QtWidgets.QVBoxLayout(self._canvas_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(0)

        canvas_layout.addWidget(_build_pane_title(tr("Configuration Canvas")))

        toolbar = QtWidgets.QHBoxLayout()
        toolbar.setContentsMargins(12, 10, 12, 8)
        toolbar.addStretch(1)

        arrange_col = QtWidgets.QPushButton(tr("Arrange: Column"))
        arrange_col.clicked.connect(lambda: self._arrange_cards(mode="column"))
        toolbar.addWidget(arrange_col)

        arrange_row = QtWidgets.QPushButton(tr("Arrange: Row"))
        arrange_row.clicked.connect(lambda: self._arrange_cards(mode="row"))
        toolbar.addWidget(arrange_row)

        add_button = QtWidgets.QPushButton(tr("+ New Config"))
        add_button.setObjectName("PrimaryButton")
        add_button.clicked.connect(self._add_config)
        toolbar.addWidget(add_button)
        canvas_layout.addLayout(toolbar)

        self.scene = QtWidgets.QGraphicsScene(self)
        self.scene.selectionChanged.connect(self._on_selection_changed)
        self.view = ConfigGraphicsView(self.scene)
        self.view.setStyleSheet("background-color: #f5f5f5; border: none;")
        self.view.viewChanged.connect(self._on_view_changed)
        canvas_layout.addWidget(self.view)

        self.placeholder = QtWidgets.QGraphicsTextItem(tr("Drop assets here"))
        self.placeholder.setDefaultTextColor(QtGui.QColor("#777777"))
        self.placeholder.setFont(QtGui.QFont("Segoe UI", 18, QtGui.QFont.Bold))
        self.scene.addItem(self.placeholder)

        self.minimap = MiniMapView(self.scene, self._canvas_container)
        self.minimap.setFixedSize(180, 120)
        self.minimap.hide()

        splitter.addWidget(self._canvas_container)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([140, 1000])
        layout.addWidget(splitter)

        self._set_detail_table_heights()

        if self._actions is None:
            self._actions = BasicActions(self._service, self._refresh_all)

        self._load_ui_state()

    def refresh(self) -> None:
        for proxy in self._proxies.values():
            self.scene.removeItem(proxy)
        self._cards.clear()
        self._proxies.clear()

        configs = self._service.list_configs()
        for index, config in enumerate(configs):
            if self._hidden.get(config.config_id, False):
                continue
            card = ConfigCardWidget(
                config,
                self._service,
                self._actions,
                self._refresh_all,
                self._request_hide_config,
                self._start_card_drag,
                self._move_card_drag,
                self._end_card_drag,
            )
            card.refresh()
            proxy = ConfigCardProxy(config.config_id, self._on_card_moved)
            proxy.setWidget(card)
            proxy.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
            proxy.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
            proxy.setCacheMode(QtWidgets.QGraphicsItem.DeviceCoordinateCache)
            proxy.setAcceptedMouseButtons(QtCore.Qt.AllButtons)

            pos = self._positions.get(config.config_id, self._default_position(index))
            proxy.setPos(pos)
            self._positions[config.config_id] = QtCore.QPointF(pos)

            self._cards[config.config_id] = card
            self._proxies[config.config_id] = proxy
            self.scene.addItem(proxy)

        self._update_placeholder()
        self._update_minimap()

    def _refresh_all(self) -> None:
        for card in self._cards.values():
            card.refresh()
        self._on_refresh_assets()

    def _set_detail_table_heights(self) -> None:
        header_height = self.detail_devices.horizontalHeader().height()
        row_height = self.detail_devices.verticalHeader().defaultSectionSize()
        target_rows = 6
        self.detail_devices.setMinimumHeight(header_height + row_height * target_rows + 8)

        header_height = self.detail_licenses.horizontalHeader().height()
        row_height = self.detail_licenses.verticalHeader().defaultSectionSize()
        self.detail_licenses.setMinimumHeight(header_height + row_height * target_rows + 8)

    def _add_config(self) -> None:
        name, ok = QtWidgets.QInputDialog.getText(
            self,
            tr("New Configuration"),
            tr("Configuration name"),
        )
        if not ok or not name.strip():
            return
        created = self._service.create_config(name=name.strip())
        self._hidden.pop(created.config_id, None)
        self._state_store.set_hidden(created.config_id, False)
        if self._toast:
            self._toast.show_message(tr("Config created"))
        if self._undo_stack:
            self._undo_stack.push(
                tr("Configuration"),
                lambda: self.show_config(created.config_id),
                lambda: self._hide_config(created.config_id, show_toast=False),
                execute=False,
            )
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

    def _on_selection_changed(self) -> None:
        selected_items = self.scene.selectedItems()
        selected_id = None
        for item in selected_items:
            for config_id, proxy in self._proxies.items():
                if proxy is item:
                    selected_id = config_id
                    break
            if selected_id is not None:
                break

        self._selected_config_id = selected_id
        if selected_id is None:
            self.detail_no.clear()
            self.detail_name.clear()
            self.detail_devices.setRowCount(0)
            self.detail_licenses.setRowCount(0)
            return

        config = self._cards[selected_id].config
        self.detail_no.setText(config.config_no)
        self.detail_name.setText(config.name)

        devices = self._service.list_config_devices(config.config_id)
        self.detail_devices.setRowCount(0)
        for device in devices:
            row = self.detail_devices.rowCount()
            self.detail_devices.insertRow(row)
            self.detail_devices.setItem(row, 0, QtWidgets.QTableWidgetItem(device.asset_no))
            self.detail_devices.setItem(row, 1, QtWidgets.QTableWidgetItem(device.device_type))
            self.detail_devices.setItem(row, 2, QtWidgets.QTableWidgetItem(device.display_name or ""))
            self.detail_devices.setItem(row, 3, QtWidgets.QTableWidgetItem(device.model))
            self.detail_devices.setItem(row, 4, QtWidgets.QTableWidgetItem(device.version))

        self.detail_devices.resizeColumnsToContents()

        licenses = self._service.list_config_licenses(config.config_id)
        self.detail_licenses.setRowCount(0)
        for license_item in licenses:
            row = self.detail_licenses.rowCount()
            self.detail_licenses.insertRow(row)
            self.detail_licenses.setItem(row, 0, QtWidgets.QTableWidgetItem(license_item.name))
            self.detail_licenses.setItem(row, 1, QtWidgets.QTableWidgetItem(license_item.license_key))
            self.detail_licenses.setItem(
                row,
                2,
                QtWidgets.QTableWidgetItem(state_display("LicenseState", license_item.state)),
            )

        self.detail_licenses.resizeColumnsToContents()


    def _load_ui_state(self) -> None:
        positions = self._state_store.load_positions()
        for config_id, (x, y, hidden) in positions.items():
            self._positions[config_id] = QtCore.QPointF(x, y)
            self._hidden[config_id] = hidden
        state = self._state_store.load_canvas_state()
        if state:
            self.view.resetTransform()
            self.view.scale(state.scale, state.scale)
            self.view.centerOn(QtCore.QPointF(state.center_x, state.center_y))

    def _on_card_moved(self, config_id: int, old_pos: QtCore.QPointF, new_pos: QtCore.QPointF) -> None:
        self._positions[config_id] = QtCore.QPointF(new_pos)
        self._state_store.save_position(config_id, new_pos.x(), new_pos.y())
        if self._toast:
            self._toast.show_message(tr("Position saved"))
        if self._undo_stack:
            def do_fn() -> None:
                proxy = self._proxies.get(config_id)
                if proxy:
                    proxy.setPos(new_pos)
                self._positions[config_id] = QtCore.QPointF(new_pos)
                self._state_store.save_position(config_id, new_pos.x(), new_pos.y())

            def undo_fn() -> None:
                proxy = self._proxies.get(config_id)
                if proxy:
                    proxy.setPos(old_pos)
                self._positions[config_id] = QtCore.QPointF(old_pos)
                self._state_store.save_position(config_id, old_pos.x(), old_pos.y())

            self._undo_stack.push(tr("Move"), do_fn, undo_fn, execute=False)

    def _start_card_drag(self, config_id: int, global_pos: QtCore.QPoint) -> None:
        proxy = self._proxies.get(config_id)
        if proxy is None:
            return
        scene_pos = self.view.mapToScene(self.view.mapFromGlobal(global_pos))
        self._dragging_id = config_id
        self._drag_start_pos = QtCore.QPointF(proxy.pos())
        self._drag_offset = scene_pos - proxy.pos()

    def _move_card_drag(self, global_pos: QtCore.QPoint) -> None:
        if self._dragging_id is None:
            return
        proxy = self._proxies.get(self._dragging_id)
        if proxy is None:
            return
        scene_pos = self.view.mapToScene(self.view.mapFromGlobal(global_pos))
        proxy.setPos(scene_pos - self._drag_offset)
        self._update_minimap()

    def _end_card_drag(self, global_pos: QtCore.QPoint) -> None:
        if self._dragging_id is None:
            return
        proxy = self._proxies.get(self._dragging_id)
        if proxy is None:
            self._dragging_id = None
            return
        scene_pos = self.view.mapToScene(self.view.mapFromGlobal(global_pos))
        new_pos = scene_pos - self._drag_offset
        snapped = self._snap_to_grid(new_pos)
        proxy.setPos(snapped)
        if snapped != self._drag_start_pos:
            self._on_card_moved(self._dragging_id, self._drag_start_pos, snapped)
        self._dragging_id = None
        self._update_minimap()

    def _snap_to_grid(self, pos: QtCore.QPointF) -> QtCore.QPointF:
        x = round(pos.x() / self.GRID_SIZE) * self.GRID_SIZE
        y = round(pos.y() / self.GRID_SIZE) * self.GRID_SIZE
        return QtCore.QPointF(x, y)

    def _arrange_cards(self, mode: str) -> None:
        self._scroll_canvas_to_origin()
        configs = [c for c in self._service.list_configs() if not self._hidden.get(c.config_id, False)]
        configs.sort(key=self._config_sort_key)
        if not configs:
            return

        viewport = self.view.viewport().rect()
        view_scene = self.view.mapToScene(viewport).boundingRect()
        margin = 20
        origin_x = view_scene.left() + margin
        origin_y = view_scene.top() + margin
        max_width = max(300, view_scene.width() - margin * 2)
        max_height = max(200, view_scene.height() - margin * 2)
        spacing = 24

        def card_size(cfg_id: int) -> QtCore.QSizeF:
            proxy = self._proxies.get(cfg_id)
            if proxy is None:
                return QtCore.QSizeF(320, 260)
            widget = proxy.widget()
            if widget is None:
                return QtCore.QSizeF(320, 260)
            hint = widget.sizeHint()
            return QtCore.QSizeF(max(280, hint.width()), max(200, hint.height()))

        x = origin_x
        y = origin_y
        line_max = 0.0

        for config in configs:
            size = card_size(config.config_id)
            if mode == "row":
                if x + size.width() > max_width:
                    x = origin_x
                    y += line_max + spacing
                    line_max = 0.0
                pos = QtCore.QPointF(x, y)
                x += size.width() + spacing
                line_max = max(line_max, size.height())
            else:
                if y + size.height() > max_height:
                    y = origin_y
                    x += line_max + spacing
                    line_max = 0.0
                pos = QtCore.QPointF(x, y)
                y += size.height() + spacing
                line_max = max(line_max, size.width())

            proxy = self._proxies.get(config.config_id)
            if proxy is None:
                continue
            snapped = self._snap_to_grid(pos)
            proxy.setPos(snapped)
            self._positions[config.config_id] = QtCore.QPointF(snapped)
            self._state_store.save_position(config.config_id, snapped.x(), snapped.y())

        if self._toast:
            self._toast.show_message(tr("Arranged"))
        self._update_minimap()

    def _scroll_canvas_to_origin(self) -> None:
        hbar = self.view.horizontalScrollBar()
        vbar = self.view.verticalScrollBar()
        hbar.setValue(hbar.minimum())
        vbar.setValue(vbar.minimum())

    def _config_sort_key(self, config: Configuration) -> tuple[int, int | str]:
        config_no = (config.config_no or "").strip()
        match = re.search(r"(\d+)", config_no)
        if match:
            return (0, int(match.group(1)))
        return (1, config.name.lower())

    def _request_hide_config(self, config_id: int) -> None:
        if self._undo_stack:
            self._undo_stack.push(
                tr("Delete"),
                lambda: self._hide_config(config_id, show_toast=True),
                lambda: self.show_config(config_id),
                execute=True,
            )
        else:
            self._hide_config(config_id, show_toast=True)

    def _hide_config(self, config_id: int, show_toast: bool = True) -> None:
        self._hidden[config_id] = True
        self._state_store.set_hidden(config_id, True)
        if show_toast and self._toast:
            self._toast.show_message(tr("Config hidden"))
        self.refresh()

    def show_config(self, config_id: int) -> None:
        self._hidden[config_id] = False
        self._state_store.set_hidden(config_id, False)
        if self._toast:
            self._toast.show_message(tr("Config restored"))
        self.refresh()

    def _on_view_changed(self) -> None:
        self._update_minimap()
        center = self.view.mapToScene(self.view.viewport().rect().center())
        scale = self.view.transform().m11()
        self._state_store.save_canvas_state(CanvasState(scale=scale, center_x=center.x(), center_y=center.y()))

    def _update_minimap(self) -> None:
        self.minimap.hide()
        return

    def center_on(self, scene_pos: QtCore.QPointF) -> None:
        self.view.centerOn(scene_pos)
        self._update_minimap()

    def set_actions(self, actions: UIActions, undo_stack: UndoStack, toast: ToastManager) -> None:
        self._actions = actions
        self._undo_stack = undo_stack
        self._toast = toast

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        margin = 12
        container = getattr(self, "_canvas_container", self)
        x = container.width() - self.minimap.width() - margin
        y = container.height() - self.minimap.height() - margin
        self.minimap.move(max(margin, x), max(margin, y))


class DevicePanel(QtWidgets.QWidget):
    def __init__(self, service: AssetService, toast: ToastManager, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._toast = toast
        self._devices: list[Device] = []

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText(tr("Search assets"))
        self.search.textChanged.connect(self._apply_filter)
        self.search.setStyleSheet(
            "QLineEdit { background-color: #ffffff; border-radius: 6px; padding: 6px 8px; color: #333333; "
            "border: 1px solid #cfcfcf; }"
        )
        layout.addWidget(self.search)

        self.device_table = AssetTableWidget("device")
        self.device_table.setColumnCount(5)
        self.device_table.setHorizontalHeaderLabels(
            [tr("Asset No"), tr("Type"), tr("Display Name"), tr("Model"), tr("Version")]
        )
        header = self.device_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        self.device_table.setStyleSheet(
            "QTableWidget { background-color: #ffffff; color: #333333; border-radius: 6px; padding: 6px; "
            "border: 1px solid #d5d5d5; gridline-color: #e3e3e3; }"
            "QHeaderView::section { background-color: #e6e6e6; color: #333333; padding: 6px; border: none; "
            "font-weight: 600; }"
            "QTableWidget::item:selected { background-color: #dbe8f6; color: #333333; }"
        )
        layout.addWidget(self.device_table, 3)

        header_height = self.device_table.horizontalHeader().height()
        row_height = self.device_table.verticalHeader().defaultSectionSize()
        self.device_table.setMinimumHeight(header_height + row_height * 12 + 8)

        button = QtWidgets.QPushButton(tr("Create Device"))
        button.setObjectName("PrimaryButton")
        button.clicked.connect(self._open_add_device)
        layout.addWidget(button)

    def refresh(self) -> None:
        self._devices = self._service.list_devices()
        self._apply_filter(self.search.text())

    def _apply_filter(self, keyword: str) -> None:
        keyword = keyword.lower().strip()
        self.device_table.setRowCount(0)
        for device in self._devices:
            label = " ".join(
                [
                    device.asset_no,
                    device.device_type,
                    device.display_name or "",
                    device.model,
                    device.version,
                ]
            ).lower()
            if not keyword or keyword in label:
                row = self.device_table.rowCount()
                self.device_table.insertRow(row)
                asset_item = QtWidgets.QTableWidgetItem(device.asset_no)
                asset_item.setData(QtCore.Qt.UserRole, device.device_id)
                self.device_table.setItem(row, 0, asset_item)
                self.device_table.setItem(row, 1, QtWidgets.QTableWidgetItem(device.device_type))
                self.device_table.setItem(row, 2, QtWidgets.QTableWidgetItem(device.display_name or ""))
                self.device_table.setItem(row, 3, QtWidgets.QTableWidgetItem(device.model))
                self.device_table.setItem(row, 4, QtWidgets.QTableWidgetItem(device.version))

            self.device_table.resizeColumnsToContents()

    def _open_add_device(self) -> None:
        dialog = DeviceCreateDialog(self._service, self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            self.refresh()
            self._toast.show_message(tr("Device created"))


class LicensePanel(QtWidgets.QWidget):
    def __init__(self, service: AssetService, toast: ToastManager, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._toast = toast
        self._licenses: list[License] = []

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText(tr("Search assets"))
        self.search.textChanged.connect(self._apply_filter)
        self.search.setStyleSheet(
            "QLineEdit { background-color: #ffffff; border-radius: 6px; padding: 6px 8px; color: #333333; "
            "border: 1px solid #cfcfcf; }"
        )
        layout.addWidget(self.search)

        self.license_table = AssetTableWidget("license")
        self.license_table.setColumnCount(3)
        self.license_table.setHorizontalHeaderLabels([tr("Subject"), tr("License Key"), tr("Status")])
        header = self.license_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        self.license_table.setStyleSheet(
            "QTableWidget { background-color: #ffffff; color: #333333; border-radius: 6px; padding: 6px; "
            "border: 1px solid #d5d5d5; gridline-color: #e3e3e3; }"
            "QHeaderView::section { background-color: #e6e6e6; color: #333333; padding: 6px; border: none; "
            "font-weight: 600; }"
            "QTableWidget::item:selected { background-color: #dbe8f6; color: #333333; }"
        )
        layout.addWidget(self.license_table, 3)

        header_height = self.license_table.horizontalHeader().height()
        row_height = self.license_table.verticalHeader().defaultSectionSize()
        self.license_table.setMinimumHeight(header_height + row_height * 10 + 8)

        button = QtWidgets.QPushButton(tr("Create License"))
        button.setObjectName("PrimaryButton")
        button.clicked.connect(self._open_add_license)
        layout.addWidget(button)

    def refresh(self) -> None:
        self._licenses = self._service.list_licenses()
        self._apply_filter(self.search.text())

    def _apply_filter(self, keyword: str) -> None:
        keyword = keyword.lower().strip()
        self.license_table.setRowCount(0)
        for license_item in self._licenses:
            label = license_item.name
            if not keyword or keyword in label.lower():
                row = self.license_table.rowCount()
                self.license_table.insertRow(row)
                name_item = QtWidgets.QTableWidgetItem(license_item.name)
                name_item.setData(QtCore.Qt.UserRole, license_item.license_id)
                self.license_table.setItem(row, 0, name_item)
                self.license_table.setItem(row, 1, QtWidgets.QTableWidgetItem(license_item.license_key))
                self.license_table.setItem(
                    row,
                    2,
                    QtWidgets.QTableWidgetItem(state_display("LicenseState", license_item.state)),
                )

        self.license_table.resizeColumnsToContents()

    def _open_add_license(self) -> None:
        dialog = LicenseCreateDialog(self._service, self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            self.refresh()
            self._toast.show_message(tr("License created"))


class DeviceCreateDialog(QtWidgets.QDialog):
    def __init__(self, service: AssetService, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._service = service
        self.setWindowTitle(tr("Create Device"))
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QGridLayout()

        self.asset_no = QtWidgets.QLineEdit()
        self.display_name = QtWidgets.QLineEdit()
        self.device_type = QtWidgets.QLineEdit()
        self.model = QtWidgets.QLineEdit()
        self.version = QtWidgets.QLineEdit()
        self.state = QtWidgets.QComboBox()
        self.state.addItems(states_display("DeviceState", ["active", "standby", "maintenance", "retired"]))
        self.note = QtWidgets.QPlainTextEdit()
        self.note.setFixedHeight(80)

        form.addWidget(QtWidgets.QLabel(tr("Asset No")), 0, 0)
        form.addWidget(self.asset_no, 0, 1)
        form.addWidget(QtWidgets.QLabel(tr("Subject")), 0, 2)
        form.addWidget(self.display_name, 0, 3)
        form.addWidget(QtWidgets.QLabel(tr("Type")), 1, 0)
        form.addWidget(self.device_type, 1, 1)
        form.addWidget(QtWidgets.QLabel(tr("Model")), 1, 2)
        form.addWidget(self.model, 1, 3)
        form.addWidget(QtWidgets.QLabel(tr("Version")), 2, 0)
        form.addWidget(self.version, 2, 1)
        form.addWidget(QtWidgets.QLabel(tr("Status")), 2, 2)
        form.addWidget(self.state, 2, 3)
        form.addWidget(QtWidgets.QLabel(tr("Description")), 3, 0)
        form.addWidget(self.note, 3, 1, 1, 3)

        layout.addLayout(form)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._submit)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _submit(self) -> None:
        asset_no = self.asset_no.text().strip()
        if not asset_no:
            QtWidgets.QMessageBox.warning(self, tr("Error"), tr("Asset No is required"))
            return
        display_name = self.display_name.text().strip() or None
        device_type = self.device_type.text().strip() or "unknown"
        model = self.model.text().strip() or "unknown"
        version = self.version.text().strip() or "-"
        state_value = state_to_physical("DeviceState", self.state.currentText(), "active")
        note = self.note.toPlainText().strip()
        self._service.add_device(
            asset_no=asset_no,
            display_name=display_name,
            device_type=device_type,
            model=model,
            version=version,
            state=state_value,
            note=note,
        )
        self.accept()


class LicenseCreateDialog(QtWidgets.QDialog):
    def __init__(self, service: AssetService, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._service = service
        self.setWindowTitle(tr("Create License"))
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QGridLayout()

        self.name = QtWidgets.QLineEdit()
        self.license_key = QtWidgets.QLineEdit()
        self.state = QtWidgets.QComboBox()
        self.state.addItems(states_display("LicenseState", ["active", "expired", "retired"]))
        self.note = QtWidgets.QPlainTextEdit()
        self.note.setFixedHeight(80)

        form.addWidget(QtWidgets.QLabel(tr("Subject")), 0, 0)
        form.addWidget(self.name, 0, 1)
        form.addWidget(QtWidgets.QLabel(tr("License Key")), 0, 2)
        form.addWidget(self.license_key, 0, 3)
        form.addWidget(QtWidgets.QLabel(tr("Status")), 1, 0)
        form.addWidget(self.state, 1, 1)
        form.addWidget(QtWidgets.QLabel(tr("Description")), 2, 0)
        form.addWidget(self.note, 2, 1, 1, 3)

        layout.addLayout(form)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._submit)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _submit(self) -> None:
        name = self.name.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, tr("Error"), tr("Subject is required"))
            return
        license_key = self.license_key.text().strip() or "-"
        state_value = state_to_physical("LicenseState", self.state.currentText(), "active")
        note = self.note.toPlainText().strip()
        self._service.add_license(
            name=name,
            license_key=license_key,
            state=state_value,
            note=note,
        )
        self.accept()


class AssetPaletteWidget(QtWidgets.QWidget):
    def __init__(self, service: AssetService, toast: ToastManager, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._toast = toast

        self.setMinimumWidth(360)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = _build_pane_title(tr("Asset Palette"))
        layout.addWidget(header)

        device_label = QtWidgets.QLabel(tr("Devices"))
        device_label.setObjectName("PaneSectionTitle")
        layout.addWidget(device_label)
        self.device_panel = DevicePanel(service, toast)
        layout.addWidget(self.device_panel, 1)

        license_label = QtWidgets.QLabel(tr("Licenses"))
        license_label.setObjectName("PaneSectionTitle")
        layout.addWidget(license_label)
        self.license_panel = LicensePanel(service, toast)
        layout.addWidget(self.license_panel, 1)

    def refresh(self) -> None:
        self.device_panel.refresh()
        self.license_panel.refresh()


class DesktopApp(QtWidgets.QMainWindow):
    def __init__(self, db_path: Optional[str] = None) -> None:
        super().__init__()
        self.setWindowTitle(tr("Desktop Asset Manager"))
        self.resize(1440, 900)

        if db_path is None:
            db_path = os.path.join(os.getcwd(), "dam.db")
        conn = init_db(db_path)

        device_repo = DeviceRepository(conn)
        license_repo = LicenseRepository(conn)
        config_repo = ConfigRepository(conn)

        self.asset_service = AssetService(device_repo, license_repo)
        self.config_service = ConfigService(config_repo)

        self._apply_theme()

        self.toast = ToastManager(self)
        self.undo_stack = UndoStack()

        splitter = QtWidgets.QSplitter()
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("QSplitter::handle { background-color: #d5d5d5; }")

        self.asset_palette = AssetPaletteWidget(self.asset_service, self.toast)
        self.canvas = ConfigCanvasWidget(
            self.config_service,
            self._refresh_assets,
            db_path,
            actions=None,
            undo_stack=self.undo_stack,
            toast=self.toast,
        )

        self.actions = UIActions(
            self.asset_service,
            self.config_service,
            self._refresh_all,
            self.toast,
            self.undo_stack,
        )
        self.canvas.set_actions(self.actions, self.undo_stack, self.toast)

        splitter.addWidget(self.asset_palette)
        splitter.addWidget(self.canvas)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([360, 1080])

        self.setCentralWidget(splitter)

        self._refresh_all()

        QtGui.QShortcut(QtGui.QKeySequence.Undo, self, activated=self._undo)
        QtGui.QShortcut(QtGui.QKeySequence.Redo, self, activated=self._redo)

    def _refresh_assets(self) -> None:
        self.asset_palette.refresh()

    def _refresh_all(self) -> None:
        self.asset_palette.refresh()
        self.canvas.refresh()

    def _undo(self) -> None:
        self.undo_stack.undo()

    def _redo(self) -> None:
        self.undo_stack.redo()

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow { background-color: #f5f5f5; }
            QWidget { font-family: Segoe UI; }
            QLabel { color: #333333; }
            QFrame#PaneTitleBar {
                background-color: #3b3b3b;
                border: 1px solid #2c2c2c;
                border-radius: 4px;
            }
            QLabel#PaneTitleText {
                color: #ffffff;
                font-weight: 700;
                font-size: 14px;
                qproperty-alignment: AlignLeft | AlignVCenter;
            }
            QLabel#PaneSectionTitle {
                color: #444444;
                font-weight: 600;
                font-size: 12px;
                margin-top: 2px;
            }
            QTabWidget::pane { border: 1px solid #d5d5d5; }
            QTabBar::tab {
                background-color: #e6e6e6;
                color: #333333;
                padding: 6px 12px;
                border: 1px solid #d5d5d5;
                border-bottom: none;
            }
            QTabBar::tab:selected { background-color: #ffffff; font-weight: 600; }
            QLineEdit, QPlainTextEdit, QComboBox {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #cfcfcf;
                border-radius: 6px;
                padding: 4px 6px;
            }
            QComboBox::drop-down { border-left: 1px solid #cfcfcf; }
            QDialog { background-color: #f5f5f5; }
            QFrame, QWidget#ConfigCard { background-color: #ffffff; }
            QScrollArea { background-color: #f5f5f5; }
            QTableWidget {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #d5d5d5;
                gridline-color: #e3e3e3;
                alternate-background-color: #fafafa;
            }
            QTableWidget::item:selected { background-color: #dbe8f6; color: #333333; }
            QHeaderView::section {
                background-color: #e6e6e6;
                color: #333333;
                font-weight: 600;
                padding: 6px;
                border: none;
            }
            QListWidget {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #d5d5d5;
            }
            QListWidget::item:selected { background-color: #dbe8f6; color: #333333; }
            QMenu {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #cfcfcf;
            }
            QMenu::item:selected { background-color: #e6f2ff; }
            QToolTip { background-color: #fff2cc; color: #333333; border: 1px solid #d5d5d5; }
            QPushButton#PrimaryButton {
                background-color: #4e8cc9;
                color: white;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
            }
            QPushButton#PrimaryButton:hover { background-color: #3c78b5; }
            QPushButton { background-color: #f0f0f0; border: 1px solid #cfcfcf; padding: 6px 10px; }
            QPushButton:hover { background-color: #e6e6e6; }
            """
        )

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self.toast.setGeometry(self.rect())


def run_app() -> None:
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    window = DesktopApp()
    window.show()
    app.exec()
