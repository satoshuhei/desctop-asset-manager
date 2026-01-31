from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from collections.abc import Callable
from typing import Dict, List, Optional

from dam.core.domain.models import Configuration, Device, License
from dam.core.services.config_service import ConfigService


class ConfigCard(ttk.LabelFrame):
    def __init__(
        self,
        master: tk.Misc,
        config: Configuration,
        service: ConfigService,
        on_refresh: callable,
    ) -> None:
        super().__init__(master, text=config.name)
        self.config_obj = config
        self._service = service
        self._on_refresh = on_refresh

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(2, 4))
        ttk.Label(header, text=f"ID: {config.config_id}").pack(side="left", padx=4)
        ttk.Button(header, text="Rename", command=self._rename).pack(side="right", padx=4)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        device_frame = ttk.LabelFrame(body, text="Devices")
        device_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.device_listbox = tk.Listbox(device_frame, height=6)
        self.device_listbox.pack(fill="both", expand=True, padx=4, pady=4)

        license_frame = ttk.LabelFrame(body, text="Licenses")
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
            self.license_listbox.insert(tk.END, license_item.name)

    def _rename(self) -> None:
        name = simpledialog.askstring("Rename", "New configuration name", parent=self)
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
        self._on_refresh = on_refresh

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=8, pady=6)
        ttk.Button(toolbar, text="+ Configuration", command=self._add_config).pack(side="left")

        self.canvas = tk.Canvas(self, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollable = ttk.Frame(self.canvas)
        self.scrollable.bind(
            "<Configure>",
            lambda _: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable, anchor="nw")

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def refresh(self) -> None:
        for child in self.scrollable.winfo_children():
            child.destroy()
        self._cards.clear()

        configs = self._service.list_configs()
        for config in configs:
            card = ConfigCard(self.scrollable, config=config, service=self._service, on_refresh=self.refresh)
            card.pack(fill="x", padx=8, pady=6)
            self._cards[config.config_id] = card

        if self._on_refresh:
            self._on_refresh()

    def _add_config(self) -> None:
        name = simpledialog.askstring("Configuration", "Configuration name", parent=self)
        if not name:
            return
        try:
            self._service.create_config(name=name)
            self.refresh()
        except Exception as exc:  # pragma: no cover - UI fallback
            messagebox.showerror("Error", str(exc))

    def get_cards(self) -> List[ConfigCard]:
        return list(self._cards.values())
