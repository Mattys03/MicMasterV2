"""
MicMaster Pro — Device Selector Widget

Dropdown for selecting audio input/output devices.
"""

import customtkinter as ctk


class DeviceSelector(ctk.CTkFrame):
    """Audio device selector with label and dropdown."""

    def __init__(self, master, label: str, devices: list, on_change=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._on_change = on_change
        self._devices = devices
        self._device_map = {}

        self._label = ctk.CTkLabel(
            self,
            text=label,
            font=("Segoe UI", 11),
            text_color="#8b949e",
            anchor="w",
        )
        self._label.pack(side="left", padx=(0, 8))

        display_names = []
        for idx, name, channels in devices:
            display = f"🎤 {name}" if "input" in label.lower() else f"🔊 {name}"
            display_names.append(display)
            self._device_map[display] = idx

        if not display_names:
            display_names = ["Nenhum dispositivo"]

        self._var = ctk.StringVar(value=display_names[0] if display_names else "")

        self._dropdown = ctk.CTkOptionMenu(
            self,
            variable=self._var,
            values=display_names,
            command=self._on_select,
            width=280,
            height=30,
            font=("Segoe UI", 11),
            dropdown_font=("Segoe UI", 10),
            fg_color="#161b22",
            button_color="#21262d",
            button_hover_color="#30363d",
            dropdown_fg_color="#161b22",
            dropdown_hover_color="#1c2333",
            text_color="#e6edf3",
            dropdown_text_color="#e6edf3",
        )
        self._dropdown.pack(side="left", fill="x", expand=True)

    def _on_select(self, choice):
        if self._on_change:
            idx = self._device_map.get(choice)
            self._on_change(idx)

    def get_selected_index(self) -> int | None:
        current = self._var.get()
        return self._device_map.get(current)

    def get_selected_raw_name(self) -> str | None:
        idx = self.get_selected_index()
        if idx is not None:
            for d_idx, raw_name, _ in self._devices:
                if d_idx == idx:
                    return raw_name
        return None

    def set_by_raw_name(self, raw_name: str) -> bool:
        for display, idx in self._device_map.items():
            for d_idx, r_name, _ in self._devices:
                if d_idx == idx and r_name == raw_name:
                    self._var.set(display)
                    return True
        return False

    def update_devices(self, devices: list, is_input: bool = True):
        self._devices = devices
        self._device_map = {}
        display_names = []
        for idx, name, channels in devices:
            icon = "🎤" if is_input else "🔊"
            display = f"{icon} {name}"
            display_names.append(display)
            self._device_map[display] = idx

        if not display_names:
            display_names = ["Nenhum dispositivo"]

        self._dropdown.configure(values=display_names)
        self._var.set(display_names[0])
