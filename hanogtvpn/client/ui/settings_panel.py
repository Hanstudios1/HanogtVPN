"""
HanogtVPN Settings Panel — Encryption, protocol, security, and general settings.
"""

import customtkinter as ctk

from hanogtvpn.client.ui.theme import Theme


class SettingsPanel(ctk.CTkScrollableFrame):
    """Settings panel with categorised sections and auto-save."""

    def __init__(self, parent, settings_manager, **kwargs):
        c = Theme.get()
        super().__init__(
            parent, fg_color=c["bg_primary"], corner_radius=0,
            scrollbar_button_color=c["scrollbar"],
            scrollbar_button_hover_color=c["text_muted"],
            **kwargs,
        )
        self.settings = settings_manager
        self._build_ui()

    def _build_ui(self):
        c = Theme.get()

        # Title
        ctk.CTkLabel(
            self, text="⚙  Ayarlar",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=c["text_primary"],
        ).pack(anchor="w", padx=30, pady=(25, 20))

        # === Connection Settings ======================================
        self._section_title("Bağlantı Ayarları")

        conn_card = self._card()

        # Encryption
        ctk.CTkLabel(
            conn_card, text="Şifreleme Tipi",
            font=ctk.CTkFont(size=13), text_color=c["text_secondary"],
        ).pack(anchor="w", padx=20, pady=(15, 5))

        self.encryption_combo = ctk.CTkComboBox(
            conn_card,
            values=["AES-256-GCM", "AES-128-GCM", "Kapalı"],
            command=self._on_encryption_change,
            width=250, height=36,
            fg_color=c["input_bg"],
            border_color=c["input_border"],
            button_color=c["accent_secondary"],
            button_hover_color=c["button_primary_hover"],
            dropdown_fg_color=c["bg_secondary"],
            dropdown_hover_color=c["bg_tertiary"],
            text_color=c["text_primary"],
        )
        enc = self.settings.get("encryption", "AES-256-GCM")
        self.encryption_combo.set(enc)
        self.encryption_combo.pack(anchor="w", padx=20, pady=(0, 15))

        # Protocol
        ctk.CTkLabel(
            conn_card, text="Protokol",
            font=ctk.CTkFont(size=13), text_color=c["text_secondary"],
        ).pack(anchor="w", padx=20, pady=(5, 5))

        self.protocol_btn = ctk.CTkSegmentedButton(
            conn_card,
            values=["TCP", "UDP"],
            command=self._on_protocol_change,
            font=ctk.CTkFont(size=13, weight="bold"),
            selected_color=c["accent_secondary"],
            selected_hover_color=c["button_primary_hover"],
            unselected_color=c["bg_tertiary"],
            unselected_hover_color=c["bg_hover"],
            text_color=c["text_primary"],
        )
        self.protocol_btn.set(self.settings.get("protocol", "TCP"))
        self.protocol_btn.pack(anchor="w", padx=20, pady=(0, 20), fill="x")

        # === Security =================================================
        self._section_title("Güvenlik")
        sec_card = self._card()

        self.kill_switch = self._toggle(
            sec_card, "Kill Switch",
            "VPN bağlantısı kesildiğinde internet erişimini engeller",
            self.settings.get("kill_switch", False),
            self._on_kill_switch,
        )

        self.dns_leak = self._toggle(
            sec_card, "DNS Sızıntı Koruması",
            "DNS sorgularını VPN tünelinden yönlendirir",
            self.settings.get("dns_leak_protection", True),
            self._on_dns_leak,
        )

        # === General ==================================================
        self._section_title("Genel")
        gen_card = self._card()

        self.auto_reconnect = self._toggle(
            gen_card, "Otomatik Yeniden Bağlan",
            "Bağlantı kesildiğinde otomatik olarak yeniden bağlanır",
            self.settings.get("auto_reconnect", True),
            self._on_auto_reconnect,
        )

        self.auto_start = self._toggle(
            gen_card, "Sistem Başlangıcında Çalıştır",
            "Bilgisayar açıldığında HanogtVPN otomatik başlar",
            self.settings.get("auto_start", False),
            self._on_auto_start,
        )

        # Log Level
        ctk.CTkLabel(
            gen_card, text="Log Seviyesi",
            font=ctk.CTkFont(size=13), text_color=c["text_secondary"],
        ).pack(anchor="w", padx=20, pady=(10, 5))

        self.log_level_combo = ctk.CTkComboBox(
            gen_card,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            command=self._on_log_level_change,
            width=200, height=36,
            fg_color=c["input_bg"],
            border_color=c["input_border"],
            button_color=c["accent_secondary"],
            button_hover_color=c["button_primary_hover"],
            dropdown_fg_color=c["bg_secondary"],
            dropdown_hover_color=c["bg_tertiary"],
            text_color=c["text_primary"],
        )
        self.log_level_combo.set(self.settings.get("log_level", "INFO"))
        self.log_level_combo.pack(anchor="w", padx=20, pady=(0, 20))

        # === About ====================================================
        self._section_title("Hakkında")
        about_card = self._card()

        about_items = [
            ("Uygulama", "HanogtVPN"),
            ("Sürüm", "1.0.0"),
            ("Şifreleme", "AES-256-GCM + ECDH + RSA-2048"),
            ("Lisans", "MIT License"),
        ]
        for label, value in about_items:
            row = ctk.CTkFrame(about_card, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=4)
            ctk.CTkLabel(
                row, text=label, font=ctk.CTkFont(size=12),
                text_color=c["text_muted"], width=120, anchor="w"
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=value, font=ctk.CTkFont(size=12, weight="bold"),
                text_color=c["text_secondary"], anchor="w"
            ).pack(side="left")

        # Add bottom padding
        ctk.CTkFrame(about_card, fg_color="transparent", height=10).pack()

    # === Helper builders ==============================================

    def _section_title(self, text: str):
        c = Theme.get()
        ctk.CTkLabel(
            self, text=text,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=c["text_muted"],
        ).pack(anchor="w", padx=30, pady=(15, 5))

    def _card(self) -> ctk.CTkFrame:
        c = Theme.get()
        card = ctk.CTkFrame(
            self, fg_color=c["card_bg"], corner_radius=12,
            border_width=1, border_color=c["border"],
        )
        card.pack(fill="x", padx=30, pady=(0, 5))
        return card

    def _toggle(self, parent, title, desc, initial, command) -> ctk.CTkSwitch:
        c = Theme.get()
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=10)

        left = ctk.CTkFrame(frame, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            left, text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=c["text_primary"], anchor="w"
        ).pack(anchor="w")

        ctk.CTkLabel(
            left, text=desc,
            font=ctk.CTkFont(size=11),
            text_color=c["text_muted"], anchor="w"
        ).pack(anchor="w")

        switch = ctk.CTkSwitch(
            frame, text="", width=48,
            command=command,
            progress_color=c["accent_primary"],
            button_color=c["text_primary"],
            button_hover_color=c["text_secondary"],
            fg_color=c["bg_tertiary"],
        )
        if initial:
            switch.select()
        else:
            switch.deselect()
        switch.pack(side="right", padx=(10, 0))

        return switch

    # === Callbacks ====================================================

    def _on_encryption_change(self, value):
        self.settings.set("encryption", value)

    def _on_protocol_change(self, value):
        self.settings.set("protocol", value)

    def _on_kill_switch(self):
        self.settings.set("kill_switch", bool(self.kill_switch.get()))

    def _on_dns_leak(self):
        self.settings.set("dns_leak_protection", bool(self.dns_leak.get()))

    def _on_auto_reconnect(self):
        self.settings.set("auto_reconnect", bool(self.auto_reconnect.get()))

    def _on_auto_start(self):
        self.settings.set("auto_start", bool(self.auto_start.get()))

    def _on_log_level_change(self, value):
        self.settings.set("log_level", value)
        from hanogtvpn.core.logger import VPNLogger
        VPNLogger.set_level(value)
