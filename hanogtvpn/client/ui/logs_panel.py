"""
HanogtVPN Logs Panel — Real-time coloured log viewer with filtering.
"""

import customtkinter as ctk

from hanogtvpn.client.ui.theme import Theme
from hanogtvpn.core.logger import VPNLogger


class LogsPanel(ctk.CTkFrame):
    """Log viewer with colour-coded entries, level filtering, and auto-scroll."""

    _LEVEL_COLORS = {
        "DEBUG": "#94A3B8",
        "INFO": "#10B981",
        "WARNING": "#F59E0B",
        "ERROR": "#EF4444",
        "CRITICAL": "#EF4444",
    }

    def __init__(self, parent, **kwargs):
        c = Theme.get()
        super().__init__(parent, fg_color=c["bg_primary"], corner_radius=0, **kwargs)
        self._auto_scroll = True
        self._filter_level = "DEBUG"
        self._all_entries: list[tuple[str, str]] = []  # (level, message)
        self._build_ui()

        # Register for log events
        VPNLogger.add_gui_handler(self._on_log)

    def _build_ui(self):
        c = Theme.get()

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(25, 10))

        ctk.CTkLabel(
            header, text="📋  Loglar",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=c["text_primary"],
        ).pack(side="left")

        # Controls
        controls = ctk.CTkFrame(header, fg_color="transparent")
        controls.pack(side="right")

        self.filter_combo = ctk.CTkComboBox(
            controls,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            command=self._on_filter_change,
            width=130, height=32,
            fg_color=c["input_bg"],
            border_color=c["input_border"],
            button_color=c["accent_secondary"],
            button_hover_color=c["button_primary_hover"],
            dropdown_fg_color=c["bg_secondary"],
            dropdown_hover_color=c["bg_tertiary"],
            text_color=c["text_primary"],
        )
        self.filter_combo.set("DEBUG")
        self.filter_combo.pack(side="left", padx=(0, 10))

        self.clear_btn = ctk.CTkButton(
            controls, text="🗑 Temizle",
            command=self._clear_logs,
            width=100, height=32,
            fg_color=c["bg_tertiary"],
            hover_color=c["bg_hover"],
            text_color=c["text_secondary"],
            corner_radius=8,
            font=ctk.CTkFont(size=12),
        )
        self.clear_btn.pack(side="left")

        # Log text area
        self.log_text = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=c["card_bg"],
            text_color=c["text_secondary"],
            corner_radius=12,
            border_width=1,
            border_color=c["border"],
            wrap="word",
            state="disabled",
        )
        self.log_text.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        # Configure text tags for colour coding
        for level, color in self._LEVEL_COLORS.items():
            self.log_text._textbox.tag_configure(level, foreground=color)

    def _on_log(self, level: str, message: str):
        """Callback from VPNLogger — invoked from any thread."""
        self._all_entries.append((level, message))
        # Limit stored entries
        if len(self._all_entries) > 2000:
            self._all_entries = self._all_entries[-1000:]

        if self._should_show(level):
            try:
                self.after(0, lambda: self._append_line(level, message))
            except Exception:
                pass

    def _should_show(self, level: str) -> bool:
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        try:
            return levels.index(level) >= levels.index(self._filter_level)
        except ValueError:
            return True

    def _append_line(self, level: str, message: str):
        self.log_text.configure(state="normal")
        self.log_text._textbox.insert("end", message + "\n", level)
        self.log_text.configure(state="disabled")
        if self._auto_scroll:
            self.log_text.see("end")

    def _on_filter_change(self, value):
        self._filter_level = value
        self._rebuild_display()

    def _rebuild_display(self):
        self.log_text.configure(state="normal")
        self.log_text._textbox.delete("1.0", "end")
        for level, msg in self._all_entries:
            if self._should_show(level):
                self.log_text._textbox.insert("end", msg + "\n", level)
        self.log_text.configure(state="disabled")
        if self._auto_scroll:
            self.log_text.see("end")

    def _clear_logs(self):
        self._all_entries.clear()
        self.log_text.configure(state="normal")
        self.log_text._textbox.delete("1.0", "end")
        self.log_text.configure(state="disabled")
