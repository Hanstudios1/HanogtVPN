"""
HanogtVPN Server List Panel — Browse, select, and add custom servers.
"""

import customtkinter as ctk
import threading

from hanogtvpn.client.ui.theme import Theme
from hanogtvpn.core.constants import DEFAULT_SERVERS
from hanogtvpn.utils.network import measure_latency
from hanogtvpn.utils.validators import validate_ip, validate_port, validate_hostname


class ServerListPanel(ctk.CTkFrame):
    """Scrollable server list with ping display and custom server entry."""

    def __init__(self, parent, settings_manager, on_server_select=None, **kwargs):
        c = Theme.get()
        super().__init__(parent, fg_color=c["bg_primary"], corner_radius=0, **kwargs)
        self.settings = settings_manager
        self._on_server_select = on_server_select
        self._selected_index = self.settings.get("selected_server_index", 0)
        self._server_cards: list[ctk.CTkFrame] = []
        self._ping_labels: list[ctk.CTkLabel] = []
        self._build_ui()
        # Measure pings in background
        threading.Thread(target=self._measure_all_pings, daemon=True).start()

    def _build_ui(self):
        c = Theme.get()

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(25, 10))

        ctk.CTkLabel(
            header, text="🌐  Sunucular",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=c["text_primary"],
        ).pack(side="left")

        refresh_btn = ctk.CTkButton(
            header, text="🔄", width=36, height=36,
            command=self._refresh_pings,
            fg_color=c["bg_tertiary"],
            hover_color=c["bg_hover"],
            text_color=c["text_secondary"],
            corner_radius=8,
        )
        refresh_btn.pack(side="right")

        # Server list (scrollable)
        list_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=c["scrollbar"],
            scrollbar_button_hover_color=c["text_muted"],
        )
        list_frame.pack(fill="both", expand=True, padx=30, pady=(0, 10))

        for idx, server in enumerate(DEFAULT_SERVERS):
            card = self._create_server_card(list_frame, server, idx)
            self._server_cards.append(card)

        self._highlight_selected()

        # === Custom Server Entry ======================================
        ctk.CTkLabel(
            self, text="Manuel Sunucu Ekle",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=c["text_muted"],
        ).pack(anchor="w", padx=30, pady=(5, 5))

        custom_card = ctk.CTkFrame(
            self, fg_color=c["card_bg"], corner_radius=12,
            border_width=1, border_color=c["border"],
        )
        custom_card.pack(fill="x", padx=30, pady=(0, 20))

        input_row = ctk.CTkFrame(custom_card, fg_color="transparent")
        input_row.pack(fill="x", padx=15, pady=15)

        self.custom_ip = ctk.CTkEntry(
            input_row, placeholder_text="IP Adresi",
            width=180, height=36,
            fg_color=c["input_bg"],
            border_color=c["input_border"],
            text_color=c["text_primary"],
            placeholder_text_color=c["text_muted"],
        )
        self.custom_ip.pack(side="left", padx=(0, 8))

        self.custom_port = ctk.CTkEntry(
            input_row, placeholder_text="Port",
            width=80, height=36,
            fg_color=c["input_bg"],
            border_color=c["input_border"],
            text_color=c["text_primary"],
            placeholder_text_color=c["text_muted"],
        )
        self.custom_port.pack(side="left", padx=(0, 8))

        connect_custom_btn = ctk.CTkButton(
            input_row, text="Bağlan",
            command=self._on_custom_connect,
            width=80, height=36,
            fg_color=c["accent_primary"],
            hover_color=c["button_connect_hover"],
            text_color="#0A0A0F",
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        connect_custom_btn.pack(side="left")

        self.custom_error = ctk.CTkLabel(
            custom_card, text="",
            font=ctk.CTkFont(size=11),
            text_color=c["accent_danger"],
        )
        self.custom_error.pack(anchor="w", padx=15, pady=(0, 10))

    def _create_server_card(self, parent, server: dict, index: int) -> ctk.CTkFrame:
        c = Theme.get()
        card = ctk.CTkFrame(
            parent, fg_color=c["card_bg"], corner_radius=12,
            border_width=1, border_color=c["border"],
            cursor="hand2",
        )
        card.pack(fill="x", pady=4)

        # Make entire card clickable
        card.bind("<Button-1>", lambda e, i=index: self._select_server(i))

        # Flag
        flag = ctk.CTkLabel(
            card, text=server.get("flag_emoji", "🌐"),
            font=ctk.CTkFont(size=26),
        )
        flag.pack(side="left", padx=(15, 10), pady=12)
        flag.bind("<Button-1>", lambda e, i=index: self._select_server(i))

        # Info
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=12)
        info.bind("<Button-1>", lambda e, i=index: self._select_server(i))

        name_lbl = ctk.CTkLabel(
            info, text=server["name"],
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=c["text_primary"], anchor="w",
        )
        name_lbl.pack(anchor="w")
        name_lbl.bind("<Button-1>", lambda e, i=index: self._select_server(i))

        detail = ctk.CTkLabel(
            info, text=f"{server['country']} • {server['host']}:{server['port']}",
            font=ctk.CTkFont(size=11),
            text_color=c["text_muted"], anchor="w",
        )
        detail.pack(anchor="w")
        detail.bind("<Button-1>", lambda e, i=index: self._select_server(i))

        # Ping
        ping_lbl = ctk.CTkLabel(
            card, text="...",
            font=ctk.CTkFont(size=12),
            text_color=c["text_muted"],
        )
        ping_lbl.pack(side="right", padx=15)
        ping_lbl.bind("<Button-1>", lambda e, i=index: self._select_server(i))
        self._ping_labels.append(ping_lbl)

        return card

    def _select_server(self, index: int):
        self._selected_index = index
        self.settings.set("selected_server_index", index)
        self._highlight_selected()
        if self._on_server_select and index < len(DEFAULT_SERVERS):
            self._on_server_select(DEFAULT_SERVERS[index])

    def _highlight_selected(self):
        c = Theme.get()
        for i, card in enumerate(self._server_cards):
            if i == self._selected_index:
                card.configure(
                    border_color=c["accent_primary"],
                    fg_color=c["bg_tertiary"],
                )
            else:
                card.configure(
                    border_color=c["border"],
                    fg_color=c["card_bg"],
                )

    def _measure_all_pings(self):
        for i, server in enumerate(DEFAULT_SERVERS):
            ping = measure_latency(server["host"], server["port"], timeout=2)
            try:
                self.after(0, lambda idx=i, p=ping: self._update_ping(idx, p))
            except Exception:
                pass

    def _update_ping(self, index: int, ping: float):
        c = Theme.get()
        if index < len(self._ping_labels):
            if ping < 0:
                self._ping_labels[index].configure(
                    text="⚫ Çevrimdışı", text_color=c["text_muted"]
                )
            elif ping < 50:
                self._ping_labels[index].configure(
                    text=f"🟢 {ping:.0f} ms", text_color=c["success"]
                )
            elif ping < 150:
                self._ping_labels[index].configure(
                    text=f"🟡 {ping:.0f} ms", text_color=c["accent_warning"]
                )
            else:
                self._ping_labels[index].configure(
                    text=f"🔴 {ping:.0f} ms", text_color=c["accent_danger"]
                )

    def _refresh_pings(self):
        c = Theme.get()
        for lbl in self._ping_labels:
            lbl.configure(text="...", text_color=c["text_muted"])
        threading.Thread(target=self._measure_all_pings, daemon=True).start()

    def _on_custom_connect(self):
        c = Theme.get()
        ip = self.custom_ip.get().strip()
        port_str = self.custom_port.get().strip()

        if not ip:
            self.custom_error.configure(text="IP adresi gerekli")
            return
        if not (validate_ip(ip) or validate_hostname(ip)):
            self.custom_error.configure(text="Geçersiz IP adresi")
            return
        if not port_str:
            port_str = "9999"
        if not validate_port(port_str):
            self.custom_error.configure(text="Geçersiz port (1-65535)")
            return

        self.custom_error.configure(text="")
        custom_server = {
            "name": f"Özel ({ip})",
            "host": ip,
            "port": int(port_str),
            "country": "Özel",
            "flag_emoji": "🔧",
        }
        if self._on_server_select:
            self._on_server_select(custom_server)
