from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Dict, List

from dam.core.domain.models import Device
from dam.core.services.asset_service import AssetService


class DeviceListView(ttk.Frame):
    def __init__(self, master: tk.Misc, service: AssetService) -> None:
        super().__init__(master)
        self._service = service
        self._items: Dict[int, Device] = {}
        self._filtered_ids: List[int] = []

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search)

        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", padx=8, pady=6)

        ttk.Label(search_frame, text="Search").pack(side="left")
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side="left", fill="x", expand=True, padx=6)

        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", padx=8, pady=(0, 6))
        ttk.Button(button_frame, text="+ Device", command=self._add_device).pack(side="left")

        self.listbox = tk.Listbox(self, height=20)
        self.listbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.refresh()

    def refresh(self) -> None:
        devices = self._service.list_devices()
        self._items = {d.device_id: d for d in devices}
        self._apply_filter(self.search_var.get())

    def _apply_filter(self, keyword: str) -> None:
        keyword_lower = keyword.lower().strip()
        self.listbox.delete(0, tk.END)
        self._filtered_ids.clear()
        for device in self._items.values():
            label = device.display_name or device.asset_no
            if not keyword_lower or keyword_lower in label.lower():
                self._filtered_ids.append(device.device_id)
                self.listbox.insert(tk.END, label)

    def _on_search(self, *_: object) -> None:
        self._apply_filter(self.search_var.get())

    def get_selected_device(self) -> Device | None:
        selection = self.listbox.curselection()
        if not selection:
            return None
        index = selection[0]
        device_id = self._filtered_ids[index]
        return self._items.get(device_id)

    def _add_device(self) -> None:
        asset_no = simpledialog.askstring("Asset No", "Asset No", parent=self)
        if not asset_no:
            return
        display_name = simpledialog.askstring("Display Name", "Display Name (optional)", parent=self)
        device_type = simpledialog.askstring("Device Type", "Device Type", parent=self) or "unknown"
        model = simpledialog.askstring("Model", "Model", parent=self) or "unknown"
        version = simpledialog.askstring("Version", "Version", parent=self) or "-"
        state = simpledialog.askstring(
            "State",
            "State (active/standby/maintenance/retired)",
            parent=self,
        ) or "active"
        note = simpledialog.askstring("Note", "Note", parent=self) or ""

        try:
            self._service.add_device(
                asset_no=asset_no,
                display_name=display_name,
                device_type=device_type,
                model=model,
                version=version,
                state=state,
                note=note,
            )
            self.refresh()
        except Exception as exc:  # pragma: no cover - UI fallback
            messagebox.showerror("Error", str(exc))
