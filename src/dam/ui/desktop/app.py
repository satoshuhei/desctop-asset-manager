from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk
from typing import Optional

from dam.core.services.asset_service import AssetService
from dam.core.services.config_service import ConfigService
from dam.infra.db import init_db
from dam.infra.repositories import ConfigRepository, DeviceRepository, LicenseRepository
from dam.ui.desktop.views.config_board import ConfigBoard, ConfigCard
from dam.ui.desktop.views.device_list import DeviceListView
from dam.ui.desktop.views.license_list import LicenseListView


class DesktopApp:
    def __init__(self, db_path: Optional[str] = None) -> None:
        self.root = tk.Tk()
        self.root.title("Desktop Asset Manager")
        self.root.geometry("1000x600")

        if db_path is None:
            db_path = os.path.join(os.getcwd(), "dam.db")
        conn = init_db(db_path)

        device_repo = DeviceRepository(conn)
        license_repo = LicenseRepository(conn)
        config_repo = ConfigRepository(conn)

        self.asset_service = AssetService(device_repo, license_repo)
        self.config_service = ConfigService(config_repo)

        self.drag_data: dict = {}

        self._build_ui()
        self.root.bind("<ButtonRelease-1>", self._on_drop)

    def _build_ui(self) -> None:
        paned = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True)

        left_frame = ttk.Frame(paned, width=320)
        right_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        paned.add(right_frame, weight=3)

        notebook = ttk.Notebook(left_frame)
        notebook.pack(fill="both", expand=True)

        self.device_view = DeviceListView(notebook, self.asset_service)
        self.license_view = LicenseListView(notebook, self.asset_service)
        notebook.add(self.device_view, text="Devices")
        notebook.add(self.license_view, text="Licenses")

        self.config_board = ConfigBoard(right_frame, self.config_service, on_refresh=self._bind_config_card_listboxes)
        self.config_board.pack(fill="both", expand=True)

        self.device_view.listbox.bind("<ButtonPress-1>", self._start_drag_device)
        self.license_view.listbox.bind("<ButtonPress-1>", self._start_drag_license)

        self._bind_config_card_listboxes()

    def _bind_config_card_listboxes(self) -> None:
        for card in self.config_board.get_cards():
            card.device_listbox.bind(
                "<ButtonPress-1>",
                lambda event, c=card: self._start_drag_config_device(event, c),
            )
            card.license_listbox.bind(
                "<ButtonPress-1>",
                lambda event, c=card: self._start_drag_config_license(event, c),
            )

    def _start_drag_device(self, event: tk.Event) -> None:
        listbox = self.device_view.listbox
        index = listbox.nearest(event.y)
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(index)
        device = self.device_view.get_selected_device()
        if device:
            self.drag_data = {
                "type": "device",
                "id": device.device_id,
                "source": "left",
            }

    def _start_drag_license(self, event: tk.Event) -> None:
        listbox = self.license_view.listbox
        index = listbox.nearest(event.y)
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(index)
        license_item = self.license_view.get_selected_license()
        if license_item:
            self.drag_data = {
                "type": "license",
                "id": license_item.license_id,
                "source": "left",
            }

    def _start_drag_config_device(self, event: tk.Event, card: ConfigCard) -> None:
        listbox = card.device_listbox
        index = listbox.nearest(event.y)
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(index)
        device = card.get_device_by_index(index)
        if device:
            self.drag_data = {
                "type": "device",
                "id": device.device_id,
                "source": "config",
                "source_config_id": card.config_obj.config_id,
            }

    def _start_drag_config_license(self, event: tk.Event, card: ConfigCard) -> None:
        listbox = card.license_listbox
        index = listbox.nearest(event.y)
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(index)
        license_item = card.get_license_by_index(index)
        if license_item:
            self.drag_data = {
                "type": "license",
                "id": license_item.license_id,
                "source": "config",
                "source_config_id": card.config_obj.config_id,
            }

    def _on_drop(self, event: tk.Event) -> None:
        if not self.drag_data:
            return

        target = self.root.winfo_containing(event.x_root, event.y_root)
        target_card, target_type = self._resolve_drop_target(target)
        if target_card is None or target_type is None:
            self.drag_data = {}
            return

        drag_type = self.drag_data.get("type")
        item_id = self.drag_data.get("id")
        source = self.drag_data.get("source")
        source_config_id = self.drag_data.get("source_config_id")

        if drag_type == "device" and target_type == "device":
            if source == "config" and source_config_id is not None:
                self.config_service.move_device(source_config_id, target_card.config_obj.config_id, item_id)
            else:
                self.config_service.assign_device(target_card.config_obj.config_id, item_id)
        elif drag_type == "license" and target_type == "license":
            self.config_service.assign_license(target_card.config_obj.config_id, item_id)
        else:
            self.drag_data = {}
            return

        self.config_board.refresh()
        self._bind_config_card_listboxes()
        self.drag_data = {}

    def _resolve_drop_target(self, widget: tk.Widget | None) -> tuple[Optional[ConfigCard], Optional[str]]:
        if widget is None:
            return None, None
        for card in self.config_board.get_cards():
            if widget == card.device_listbox:
                return card, "device"
            if widget == card.license_listbox:
                return card, "license"
        return None, None

    def run(self) -> None:
        self.root.mainloop()


def run_app() -> None:
    DesktopApp().run()
