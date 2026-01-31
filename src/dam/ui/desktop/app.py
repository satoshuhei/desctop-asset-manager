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
        self._drag_preview: Optional[tk.Toplevel] = None
        self._drag_preview_label: Optional[tk.Label] = None
        self._hover_target: Optional[tk.Widget] = None
        self._hover_target_bg: dict[tk.Widget, str] = {}

        self._build_ui()
        self.root.bind("<B1-Motion>", self._on_drag_motion)
        self.root.bind("<ButtonRelease-1>", self._on_drop)

    def _build_ui(self) -> None:
        main_notebook = ttk.Notebook(self.root)
        main_notebook.pack(fill="both", expand=True)

        assets_tab = ttk.Frame(main_notebook)
        configs_tab = ttk.Frame(main_notebook)
        main_notebook.add(assets_tab, text="Assets")
        main_notebook.add(configs_tab, text="Configurations")

        assets_notebook = ttk.Notebook(assets_tab)
        assets_notebook.pack(fill="both", expand=True)

        self.device_admin_view = DeviceListView(
            assets_notebook,
            self.asset_service,
            show_form=True,
            on_change=self._refresh_asset_views,
        )
        self.license_admin_view = LicenseListView(
            assets_notebook,
            self.asset_service,
            show_form=True,
            on_change=self._refresh_asset_views,
        )
        assets_notebook.add(self.device_admin_view, text="Devices")
        assets_notebook.add(self.license_admin_view, text="Licenses")

        paned = ttk.Panedwindow(configs_tab, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True)

        left_frame = ttk.Frame(paned, width=320)
        right_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        paned.add(right_frame, weight=3)

        config_assets_notebook = ttk.Notebook(left_frame)
        config_assets_notebook.pack(fill="both", expand=True)

        self.device_view = DeviceListView(config_assets_notebook, self.asset_service, show_form=False)
        self.license_view = LicenseListView(config_assets_notebook, self.asset_service, show_form=False)
        config_assets_notebook.add(self.device_view, text="Devices")
        config_assets_notebook.add(self.license_view, text="Licenses")

        self.config_board = ConfigBoard(right_frame, self.config_service, on_refresh=self._bind_config_card_listboxes)
        self.config_board.pack(fill="both", expand=True)
        self.config_board.refresh()

        self.device_view.tree.bind("<ButtonPress-1>", self._start_drag_device)
        self.license_view.tree.bind("<ButtonPress-1>", self._start_drag_license)

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
        tree = self.device_view.tree
        row_id = tree.identify_row(event.y)
        if not row_id:
            return
        tree.selection_set(row_id)
        device = self.device_view.get_selected_device()
        if device:
            self.drag_data = {
                "type": "device",
                "id": device.device_id,
                "source": "left",
            }
            self._begin_drag(event, device.display_name or device.asset_no)

    def _start_drag_license(self, event: tk.Event) -> None:
        tree = self.license_view.tree
        row_id = tree.identify_row(event.y)
        if not row_id:
            return
        tree.selection_set(row_id)
        license_item = self.license_view.get_selected_license()
        if license_item:
            self.drag_data = {
                "type": "license",
                "id": license_item.license_id,
                "source": "left",
            }
            self._begin_drag(event, license_item.name)

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
            self._begin_drag(event, device.display_name or device.asset_no)

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
            self._begin_drag(event, license_item.name)

    def _begin_drag(self, event: tk.Event, label: str) -> None:
        if self._drag_preview is None:
            preview = tk.Toplevel(self.root)
            preview.overrideredirect(True)
            preview.attributes("-topmost", True)
            preview.configure(bg="#222222")
            self._drag_preview = preview
            self._drag_preview_label = tk.Label(
                preview,
                text=label,
                fg="white",
                bg="#222222",
                padx=8,
                pady=4,
            )
            self._drag_preview_label.pack()
        elif self._drag_preview_label is not None:
            self._drag_preview_label.configure(text=label)

        self._move_drag_preview(event.x_root, event.y_root)

    def _move_drag_preview(self, x_root: int, y_root: int) -> None:
        if self._drag_preview is None:
            return
        offset = 12
        self._drag_preview.geometry(f"+{x_root + offset}+{y_root + offset}")

    def _on_drag_motion(self, event: tk.Event) -> None:
        if not self.drag_data:
            return
        self._move_drag_preview(event.x_root, event.y_root)

        target = self.root.winfo_containing(event.x_root, event.y_root)
        target_card, target_type = self._resolve_drop_target(target)
        target_widget: Optional[tk.Widget] = None
        if target_card is not None and target_type == "device":
            target_widget = target_card.device_listbox
        elif target_card is not None and target_type == "license":
            target_widget = target_card.license_listbox

        self._set_hover_target(target_widget)

    def _set_hover_target(self, widget: Optional[tk.Widget]) -> None:
        if widget == self._hover_target:
            return

        if self._hover_target is not None:
            original = self._hover_target_bg.get(self._hover_target)
            if original is not None:
                self._hover_target.configure(background=original)

        self._hover_target = widget
        if widget is not None:
            if widget not in self._hover_target_bg:
                self._hover_target_bg[widget] = widget.cget("background")
            widget.configure(background="#dbeafe")

    def _on_drop(self, event: tk.Event) -> None:
        if not self.drag_data:
            return

        target = self.root.winfo_containing(event.x_root, event.y_root)
        target_card, target_type = self._resolve_drop_target(target)
        if target_card is None or target_type is None:
            self.drag_data = {}
            self._cleanup_drag_ui()
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
            self._cleanup_drag_ui()
            return

        self.config_board.refresh()
        self._bind_config_card_listboxes()
        self._refresh_asset_views()
        self.drag_data = {}
        self._cleanup_drag_ui()

    def _resolve_drop_target(self, widget: tk.Widget | None) -> tuple[Optional[ConfigCard], Optional[str]]:
        if widget is None:
            return None, None
        for card in self.config_board.get_cards():
            if widget == card.device_listbox:
                return card, "device"
            if widget == card.license_listbox:
                return card, "license"
        return None, None

    def _cleanup_drag_ui(self) -> None:
        self._set_hover_target(None)
        if self._drag_preview is not None:
            self._drag_preview.destroy()
            self._drag_preview = None
            self._drag_preview_label = None

    def _refresh_asset_views(self) -> None:
        self.device_view.refresh()
        self.license_view.refresh()
        self.device_admin_view.refresh()
        self.license_admin_view.refresh()

    def run(self) -> None:
        self.root.mainloop()


def run_app() -> None:
    DesktopApp().run()
