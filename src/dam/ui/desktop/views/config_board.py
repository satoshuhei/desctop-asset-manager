from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from collections.abc import Callable
from typing import Dict, List, Optional

from dam.core.domain.models import Configuration, Device, License
from dam.core.services.config_service import ConfigService
from dam.ui.i18n import tr


class ConfigCard(ttk.LabelFrame):
    def __init__(
        self,
        master: tk.Misc,
        config: Configuration,
        service: ConfigService,
        on_refresh: callable,
    ) -> None:
        super().__init__(master, text=config.name, style="Card.TLabelframe")
        self.config_obj = config
        self._service = service
        self._on_refresh = on_refresh

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(2, 4))
        self.drag_handle = ttk.Label(header, text="⠿", style="Handle.TLabel", cursor="fleur")
        self.drag_handle.pack(side="left", padx=(4, 2))
        ttk.Label(header, text=tr("ID: {id}", id=config.config_id)).pack(side="left", padx=4)
        ttk.Button(header, text=tr("Rename"), command=self._rename).pack(side="right", padx=4)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        device_frame = ttk.LabelFrame(body, text=tr("Devices"))
        device_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.device_listbox = tk.Listbox(device_frame, height=6)
        self.device_listbox.pack(fill="both", expand=True, padx=4, pady=4)

        license_frame = ttk.LabelFrame(body, text=tr("Licenses"))
        license_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.license_listbox = tk.Listbox(license_frame, height=6)
        self.license_listbox.pack(fill="both", expand=True, padx=4, pady=4)

        self._device_items: Dict[int, Device] = {}
        self._license_items: Dict[int, License] = {}
        self.refresh()

        self.device_listbox.bind("<Delete>", self._remove_device)
        self.license_listbox.bind("<Delete>", self._remove_license)

    def refresh(self) -> None:
        devices = self._service.list_config_devices(self.config_obj.config_id)
        licenses = self._service.list_config_licenses(self.config_obj.config_id)
        self._device_items = {d.device_id: d for d in devices}
        self._license_items = {l.license_id: l for l in licenses}

        self.device_listbox.delete(0, tk.END)
        for device in devices:
            label = device.display_name or device.asset_no
            self.device_listbox.insert(tk.END, label)

        self.license_listbox.delete(0, tk.END)
        for license_item in licenses:
            self.license_listbox.insert(tk.END, f"{license_item.license_no} {license_item.name}")

    def _rename(self) -> None:
        name = simpledialog.askstring(tr("Rename"), tr("New configuration name"), parent=self)
        if not name:
            return
        self._service.rename_config(self.config_obj.config_id, name)
        self.config(text=name)
        self._on_refresh()

    def _remove_device(self, _: tk.Event) -> None:
        selection = self.device_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        device_id = list(self._device_items.keys())[index]
        self._service.unassign_device(self.config_obj.config_id, device_id)
        self.refresh()

    def _remove_license(self, _: tk.Event) -> None:
        selection = self.license_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        license_id = list(self._license_items.keys())[index]
        self._service.unassign_license(self.config_obj.config_id, license_id)
        self.refresh()

    def get_device_by_index(self, index: int) -> Optional[Device]:
        device_ids = list(self._device_items.keys())
        if index < 0 or index >= len(device_ids):
            return None
        return self._device_items[device_ids[index]]

    def get_license_by_index(self, index: int) -> Optional[License]:
        license_ids = list(self._license_items.keys())
        if index < 0 or index >= len(license_ids):
            return None
        return self._license_items[license_ids[index]]


class ConfigBoard(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        service: ConfigService,
        on_refresh: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master)
        self._service = service
        self._cards: Dict[int, ConfigCard] = {}
        self._card_windows: Dict[int, int] = {}
        self._positions: Dict[int, tuple[int, int]] = {}
        self._dragging_id: Optional[int] = None
        self._drag_offset: tuple[int, int] = (0, 0)
        self._on_refresh = on_refresh

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=8, pady=6)
        ttk.Button(toolbar, text=tr("+ Configuration"), command=self._add_config).pack(side="left")

        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, background="#f5f7fb")
        self.v_scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.h_scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.v_scrollbar.pack(side="right", fill="y")
        self.h_scrollbar.pack(side="bottom", fill="x")

    def refresh(self) -> None:
        for window_id in self._card_windows.values():
            self.canvas.delete(window_id)
        self._cards.clear()
        self._card_windows.clear()

        configs = self._service.list_configs()
        for index, config in enumerate(configs):
            card = ConfigCard(self.canvas, config=config, service=self._service, on_refresh=self.refresh)
            self._cards[config.config_id] = card

            x, y = self._positions.get(config.config_id, self._default_position(index))
            self._positions[config.config_id] = (x, y)
            window_id = self.canvas.create_window(x, y, window=card, anchor="nw", width=360)
            self._card_windows[config.config_id] = window_id

            card.drag_handle.bind("<ButtonPress-1>", lambda event, cid=config.config_id: self._start_drag(event, cid))
            card.drag_handle.bind("<B1-Motion>", self._on_drag)
            card.drag_handle.bind("<ButtonRelease-1>", self._end_drag)

        self._update_scrollregion()

        if self._on_refresh:
            self._on_refresh()

    def _add_config(self) -> None:
        name = simpledialog.askstring(tr("Configuration"), tr("Configuration name"), parent=self)
        if not name:
            return
        try:
            self._service.create_config(name=name)
            self.refresh()
        except Exception as exc:  # pragma: no cover - UI fallback
            messagebox.showerror(tr("Error"), str(exc))

    def _default_position(self, index: int) -> tuple[int, int]:
        col = index % 2
        row = index // 2
        x = 20 + col * 400
        y = 20 + row * 320
        return x, y

    def _start_drag(self, event: tk.Event, config_id: int) -> None:
        self._dragging_id = config_id
        window_id = self._card_windows.get(config_id)
        if window_id is None:
            return
        coords = self.canvas.coords(window_id)
        canvas_x = self.canvas.canvasx(event.x_root - self.canvas.winfo_rootx())
        canvas_y = self.canvas.canvasy(event.y_root - self.canvas.winfo_rooty())
        self._drag_offset = (int(canvas_x - coords[0]), int(canvas_y - coords[1]))

    def _on_drag(self, event: tk.Event) -> None:
        if self._dragging_id is None:
            return
        window_id = self._card_windows.get(self._dragging_id)
        if window_id is None:
            return
        canvas_x = self.canvas.canvasx(event.x_root - self.canvas.winfo_rootx())
        canvas_y = self.canvas.canvasy(event.y_root - self.canvas.winfo_rooty())
        x = int(canvas_x - self._drag_offset[0])
        y = int(canvas_y - self._drag_offset[1])
        self.canvas.coords(window_id, x, y)
        self._positions[self._dragging_id] = (x, y)
        self._update_scrollregion()

    def _end_drag(self, _: tk.Event) -> None:
        self._dragging_id = None

    def _update_scrollregion(self) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def get_cards(self) -> List[ConfigCard]:
        return list(self._cards.values())
