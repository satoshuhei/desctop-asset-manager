from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Dict, List

from dam.core.domain.models import Device
from dam.core.services.asset_service import AssetService


class DeviceListView(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        service: AssetService,
        show_form: bool = True,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master)
        self._service = service
        self._items: Dict[int, Device] = {}
        self._filtered_ids: List[int] = []
        self._on_change = on_change

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search)

        filter_frame = ttk.LabelFrame(self, text="Filters")
        filter_frame.pack(fill="x", padx=8, pady=6)

        ttk.Label(filter_frame, text="Search").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(filter_frame, textvariable=self.search_var).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=6,
            pady=6,
        )
        filter_frame.columnconfigure(1, weight=1)

        if show_form:
            self._build_form()

        list_frame = ttk.LabelFrame(self, text="Tickets")
        list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        columns = ("subject", "asset_no", "device_type", "model", "version", "state")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=14, selectmode="browse")
        self.tree.heading("subject", text="Subject")
        self.tree.heading("asset_no", text="Asset No")
        self.tree.heading("device_type", text="Type")
        self.tree.heading("model", text="Model")
        self.tree.heading("version", text="Version")
        self.tree.heading("state", text="Status")

        self.tree.column("subject", width=200, anchor="w")
        self.tree.column("asset_no", width=100, anchor="w")
        self.tree.column("device_type", width=120, anchor="w")
        self.tree.column("model", width=140, anchor="w")
        self.tree.column("version", width=80, anchor="w")
        self.tree.column("state", width=80, anchor="center")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.refresh()

    def _build_form(self) -> None:
        form_frame = ttk.LabelFrame(self, text="New Device Ticket")
        form_frame.pack(fill="x", padx=8, pady=(0, 8))

        self.asset_no_var = tk.StringVar()
        self.display_name_var = tk.StringVar()
        self.device_type_var = tk.StringVar()
        self.model_var = tk.StringVar()
        self.version_var = tk.StringVar()
        self.state_var = tk.StringVar(value="active")

        ttk.Label(form_frame, text="Asset No").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(form_frame, textvariable=self.asset_no_var).grid(row=0, column=1, sticky="ew", padx=6, pady=4)

        ttk.Label(form_frame, text="Subject").grid(row=0, column=2, sticky="w", padx=6, pady=4)
        ttk.Entry(form_frame, textvariable=self.display_name_var).grid(row=0, column=3, sticky="ew", padx=6, pady=4)

        ttk.Label(form_frame, text="Type").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(form_frame, textvariable=self.device_type_var).grid(row=1, column=1, sticky="ew", padx=6, pady=4)

        ttk.Label(form_frame, text="Model").grid(row=1, column=2, sticky="w", padx=6, pady=4)
        ttk.Entry(form_frame, textvariable=self.model_var).grid(row=1, column=3, sticky="ew", padx=6, pady=4)

        ttk.Label(form_frame, text="Version").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(form_frame, textvariable=self.version_var).grid(row=2, column=1, sticky="ew", padx=6, pady=4)

        ttk.Label(form_frame, text="Status").grid(row=2, column=2, sticky="w", padx=6, pady=4)
        ttk.Combobox(
            form_frame,
            textvariable=self.state_var,
            values=["active", "standby", "maintenance", "retired"],
            state="readonly",
        ).grid(row=2, column=3, sticky="ew", padx=6, pady=4)

        ttk.Label(form_frame, text="Description").grid(row=3, column=0, sticky="nw", padx=6, pady=4)
        self.note_text = tk.Text(form_frame, height=3, wrap="word")
        self.note_text.grid(row=3, column=1, columnspan=3, sticky="ew", padx=6, pady=4)

        form_frame.columnconfigure(1, weight=1)
        form_frame.columnconfigure(3, weight=1)

        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=4, column=0, columnspan=4, sticky="e", padx=6, pady=6)
        ttk.Button(button_frame, text="Create Device", command=self._add_device).pack(side="right")

    def refresh(self) -> None:
        devices = self._service.list_devices()
        self._items = {d.device_id: d for d in devices}
        self._apply_filter(self.search_var.get())

    def _apply_filter(self, keyword: str) -> None:
        keyword_lower = keyword.lower().strip()
        self.tree.delete(*self.tree.get_children())
        self._filtered_ids.clear()
        for device in self._items.values():
            label = device.display_name or device.asset_no
            if not keyword_lower or keyword_lower in label.lower():
                self._filtered_ids.append(device.device_id)
                self.tree.insert(
                    "",
                    "end",
                    iid=str(device.device_id),
                    values=(
                        label,
                        device.asset_no,
                        device.device_type,
                        device.model,
                        device.version,
                        device.state,
                    ),
                )

    def _on_search(self, *_: object) -> None:
        self._apply_filter(self.search_var.get())

    def get_selected_device(self) -> Device | None:
        selection = self.tree.selection()
        if not selection:
            return None
        device_id = int(selection[0])
        return self._items.get(device_id)

    def _add_device(self) -> None:
        asset_no = self.asset_no_var.get().strip()
        if not asset_no:
            messagebox.showerror("Error", "Asset No is required")
            return
        display_name = self.display_name_var.get().strip() or None
        device_type = self.device_type_var.get().strip() or "unknown"
        model = self.model_var.get().strip() or "unknown"
        version = self.version_var.get().strip() or "-"
        state = self.state_var.get().strip() or "active"
        note = self.note_text.get("1.0", "end").strip()

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
            if self._on_change:
                self._on_change()
            self.asset_no_var.set("")
            self.display_name_var.set("")
            self.device_type_var.set("")
            self.model_var.set("")
            self.version_var.set("")
            self.state_var.set("active")
            self.note_text.delete("1.0", "end")
        except Exception as exc:  # pragma: no cover - UI fallback
            messagebox.showerror("Error", str(exc))
