"""
HanogtVPN Main Panel — Connection dashboard with status, stats, and connect button.
"""

import customtkinter as ctk
import time

from hanogtvpn.client.ui.theme import Theme
from hanogtvpn.core.constants import ConnectionState
from hanogtvpn.utils.network import format_bytes, format_speed


class MainPanel(ctk.CTkFrame):
    """Primary dashboard panel showing connection status, stats, and controls."""

    def __init__(self, parent, connection_manager, settings_manager, **kwargs):
        c = Theme.get()
        super().__init__(parent, fg_color=c["bg_primary"], corner_radius=0, **kwargs)
        self.conn = connection_manager
        self.settings = settings_manager
        self._timer_id = None

        self._build_ui()

        # Register callbacks
        self.conn.add_state_callback(self._on_state_change)
        self.conn.add_stats_callback(self._on_stats_update)

    def _build_ui(self):
        c = Theme.get()

        # === Status Header ============================================
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.pack(fill="x", padx=30, pady=(30, 10))

        self.status_icon = ctk.CTkLabel(
            status_frame, text="⬤", font=ctk.CTkFont(size=18),
            text_color=c["accent_danger"]
        )
        self.status_icon.pack(side="left", padx=(0, 10))

        self.status_label = ctk.CTkLabel(
            status_frame, text="Bağlı Değil",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=c["accent_danger"]
        )
        self.status_label.pack(side="left")

        self.ping_label = ctk.CTkLabel(
            status_frame, text="",
            font=ctk.CTkFont(size=13),
            text_color=c["text_muted"]
        )
        self.ping_label.pack(side="right", padx=10)

        # === Selected Server Card =====================================
        server_card = ctk.CTkFrame(
            self, fg_color=c["card_bg"], corner_radius=12, border_width=1,
            border_color=c["border"]
        )
        server_card.pack(fill="x", padx=30, pady=(10, 5))

        self.server_flag = ctk.CTkLabel(
            server_card, text="🇹🇷", font=ctk.CTkFont(size=28)
        )
        self.server_flag.pack(side="left", padx=(20, 10), pady=15)

        server_info = ctk.CTkFrame(server_card, fg_color="transparent")
        server_info.pack(side="left", fill="x", expand=True, pady=15)

        self.server_name_label = ctk.CTkLabel(
            server_info, text="İstanbul",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=c["text_primary"], anchor="w"
        )
        self.server_name_label.pack(anchor="w")

        self.server_detail_label = ctk.CTkLabel(
            server_info, text="127.0.0.1:9999 • TCP • AES-256-GCM",
            font=ctk.CTkFont(size=12),
            text_color=c["text_muted"], anchor="w"
        )
        self.server_detail_label.pack(anchor="w")

        # === Connect Button (Big, Styled) ==============================
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=25)

        self.connect_btn = ctk.CTkButton(
            btn_frame,
            text="⚡  BAĞLAN",
            command=self._on_connect_click,
            width=320, height=70,
            font=ctk.CTkFont(size=22, weight="bold"),
            corner_radius=35,
            fg_color=c["accent_primary"],
            hover_color=c["button_connect_hover"],
            text_color="#0A0A0F",
        )
        self.connect_btn.pack()

        # === Stats Grid ===============================================
        stats_frame = ctk.CTkFrame(
            self, fg_color=c["card_bg"], corner_radius=12,
            border_width=1, border_color=c["border"]
        )
        stats_frame.pack(fill="x", padx=30, pady=(5, 10))
        stats_frame.grid_columnconfigure((0, 1), weight=1)

        # Upload
        self._stat_upload = self._create_stat_card(
            stats_frame, "↑ Yükleme", "0 B", "0 B/s", 0, 0
        )
        # Download
        self._stat_download = self._create_stat_card(
            stats_frame, "↓ İndirme", "0 B", "0 B/s", 0, 1
        )
        # Duration
        self._stat_duration = self._create_stat_card(
            stats_frame, "⏱ Süre", "00:00:00", "", 1, 0
        )
        # Ping
        self._stat_ping = self._create_stat_card(
            stats_frame, "📡 Ping", "— ms", "", 1, 1
        )

        # === Connection Info ==========================================
        info_frame = ctk.CTkFrame(
            self, fg_color=c["card_bg"], corner_radius=12,
            border_width=1, border_color=c["border"]
        )
        info_frame.pack(fill="x", padx=30, pady=(5, 20))

        info_title = ctk.CTkLabel(
            info_frame, text="Bağlantı Bilgileri",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=c["text_secondary"]
        )
        info_title.pack(anchor="w", padx=20, pady=(12, 8))

        info_grid = ctk.CTkFrame(info_frame, fg_color="transparent")
        info_grid.pack(fill="x", padx=20, pady=(0, 12))
        info_grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.info_protocol = self._info_item(info_grid, "Protokol", "TCP", 0)
        self.info_encryption = self._info_item(info_grid, "Şifreleme", "AES-256-GCM", 1)
        self.info_socks5 = self._info_item(info_grid, "SOCKS5 Proxy", "Kapalı", 2)
        self.info_status = self._info_item(info_grid, "Durum", "Bağlı Değil", 3)

    def _create_stat_card(self, parent, title, value, sub, row, col):
        c = Theme.get()
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=col, padx=15, pady=12, sticky="w")

        lbl_title = ctk.CTkLabel(
            frame, text=title, font=ctk.CTkFont(size=12),
            text_color=c["text_muted"]
        )
        lbl_title.pack(anchor="w")

        lbl_value = ctk.CTkLabel(
            frame, text=value, font=ctk.CTkFont(size=18, weight="bold"),
            text_color=c["text_primary"]
        )
        lbl_value.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            frame, text=sub, font=ctk.CTkFont(size=11),
            text_color=c["accent_primary"]
        )
        lbl_sub.pack(anchor="w")

        return {"title": lbl_title, "value": lbl_value, "sub": lbl_sub}

    def _info_item(self, parent, label, value, col):
        c = Theme.get()
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=0, column=col, sticky="w")

        ctk.CTkLabel(
            frame, text=label, font=ctk.CTkFont(size=11),
            text_color=c["text_muted"]
        ).pack(anchor="w")

        val_lbl = ctk.CTkLabel(
            frame, text=value, font=ctk.CTkFont(size=13, weight="bold"),
            text_color=c["text_secondary"]
        )
        val_lbl.pack(anchor="w")
        return val_lbl

    # === Server Info Update ==========================================

    def update_server_info(self, server: dict):
        """Called when user selects a server."""
        self.server_flag.configure(text=server.get("flag_emoji", "🌐"))
        self.server_name_label.configure(text=server.get("name", "Unknown"))
        enc = self.settings.get("encryption", "AES-256-GCM")
        proto = self.settings.get("protocol", "TCP")
        detail = f"{server['host']}:{server['port']} • {proto} • {enc}"
        self.server_detail_label.configure(text=detail)

    # === Button Callback =============================================

    def _on_connect_click(self):
        if self.conn.state == ConnectionState.CONNECTED:
            self.conn.disconnect()
        elif self.conn.state == ConnectionState.DISCONNECTED or \
             self.conn.state == ConnectionState.ERROR:
            from hanogtvpn.core.constants import DEFAULT_SERVERS
            idx = self.settings.get("selected_server_index", 0)
            servers = DEFAULT_SERVERS
            if 0 <= idx < len(servers):
                srv = servers[idx]
            else:
                srv = servers[0]
            self.conn.connect(srv["host"], srv["port"])

    # === Callbacks from ConnectionManager ============================

    def _on_state_change(self, state: ConnectionState):
        c = Theme.get()
        if state == ConnectionState.DISCONNECTED:
            self.status_icon.configure(text="⬤", text_color=c["accent_danger"])
            self.status_label.configure(text="Bağlı Değil", text_color=c["accent_danger"])
            self.connect_btn.configure(
                text="⚡  BAĞLAN",
                fg_color=c["accent_primary"],
                hover_color=c["button_connect_hover"],
                text_color="#0A0A0F",
            )
            self.info_status.configure(text="Bağlı Değil")
            self.info_socks5.configure(text="Kapalı")
            self.ping_label.configure(text="")
            self._stop_timer()

        elif state == ConnectionState.CONNECTING:
            self.status_icon.configure(text="⬤", text_color=c["accent_warning"])
            self.status_label.configure(text="Bağlanıyor...", text_color=c["accent_warning"])
            self.connect_btn.configure(
                text="⏳  BAĞLANIYOR...",
                fg_color=c["button_connecting"],
                hover_color=c["accent_warning"],
                text_color="#0A0A0F",
            )
            self.info_status.configure(text="Bağlanıyor...")

        elif state == ConnectionState.CONNECTED:
            self.status_icon.configure(text="⬤", text_color=c["success"])
            self.status_label.configure(text="Bağlandı", text_color=c["success"])
            self.connect_btn.configure(
                text="⛔  BAĞLANTIYI KES",
                fg_color=c["accent_danger"],
                hover_color=c["button_disconnect_hover"],
                text_color="#FFFFFF",
            )
            self.info_status.configure(text="Bağlı")
            self.info_socks5.configure(text="127.0.0.1:1080")
            self.ping_label.configure(
                text=f"📡 {self.conn.current_ping} ms"
            )
            self._start_timer()

        elif state == ConnectionState.ERROR:
            self.status_icon.configure(text="⬤", text_color=c["accent_danger"])
            self.status_label.configure(text="Bağlantı Hatası", text_color=c["accent_danger"])
            self.connect_btn.configure(
                text="⚡  YENİDEN BAĞLAN",
                fg_color=c["accent_primary"],
                hover_color=c["button_connect_hover"],
                text_color="#0A0A0F",
            )
            self.info_status.configure(text="Hata")
            self._stop_timer()

    def _on_stats_update(self, stats: dict):
        self._stat_upload["value"].configure(text=format_bytes(stats["bytes_sent"]))
        self._stat_upload["sub"].configure(text=format_speed(stats["upload_speed"]))
        self._stat_download["value"].configure(text=format_bytes(stats["bytes_received"]))
        self._stat_download["sub"].configure(text=format_speed(stats["download_speed"]))

        if stats["ping"] >= 0:
            self._stat_ping["value"].configure(text=f"{stats['ping']} ms")

    def _start_timer(self):
        self._update_timer()

    def _stop_timer(self):
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None
        self._stat_duration["value"].configure(text="00:00:00")

    def _update_timer(self):
        if self.conn.state != ConnectionState.CONNECTED:
            return
        if self.conn.connected_since:
            elapsed = int(time.time() - self.conn.connected_since)
            h = elapsed // 3600
            m = (elapsed % 3600) // 60
            s = elapsed % 60
            self._stat_duration["value"].configure(text=f"{h:02d}:{m:02d}:{s:02d}")
        self._timer_id = self.after(1000, self._update_timer)
