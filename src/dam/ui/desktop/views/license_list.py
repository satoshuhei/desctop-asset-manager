from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Dict, List

from dam.core.domain.models import License
from dam.core.services.asset_service import AssetService


class LicenseListView(ttk.Frame):
    def __init__(self, master: tk.Misc, service: AssetService) -> None:
        super().__init__(master)
        self._service = service
        self._items: Dict[int, License] = {}
        self._filtered_ids: List[int] = []

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search)

        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", padx=8, pady=6)

        ttk.Label(search_frame, text="Search").pack(side="left")
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side="left", fill="x", expand=True, padx=6)

        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", padx=8, pady=(0, 6))
        ttk.Button(button_frame, text="+ License", command=self._add_license).pack(side="left")

        self.listbox = tk.Listbox(self, height=20)
        self.listbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.refresh()

    def refresh(self) -> None:
        licenses = self._service.list_licenses()
        self._items = {l.license_id: l for l in licenses}
        self._apply_filter(self.search_var.get())

    def _apply_filter(self, keyword: str) -> None:
        keyword_lower = keyword.lower().strip()
        self.listbox.delete(0, tk.END)
        self._filtered_ids.clear()
        for license_item in self._items.values():
            label = license_item.name
            if not keyword_lower or keyword_lower in label.lower():
                self._filtered_ids.append(license_item.license_id)
                self.listbox.insert(tk.END, label)

    def _on_search(self, *_: object) -> None:
        self._apply_filter(self.search_var.get())

    def get_selected_license(self) -> License | None:
        selection = self.listbox.curselection()
        if not selection:
            return None
        index = selection[0]
        license_id = self._filtered_ids[index]
        return self._items.get(license_id)

    def _add_license(self) -> None:
        name = simpledialog.askstring("Name", "License name", parent=self)
        if not name:
            return
        license_key = simpledialog.askstring("Key", "License key", parent=self) or "-"
        state = simpledialog.askstring("State", "State (active/expired/retired)", parent=self) or "active"
        note = simpledialog.askstring("Note", "Note", parent=self) or ""

        try:
            self._service.add_license(
                name=name,
                license_key=license_key,
                state=state,
                note=note,
            )
            self.refresh()
        except Exception as exc:  # pragma: no cover - UI fallback
            messagebox.showerror("Error", str(exc))
