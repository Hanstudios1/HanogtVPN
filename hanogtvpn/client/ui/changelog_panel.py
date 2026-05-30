"""
HanogtVPN Changelog Panel - Displays version updates and changes.
"""

import customtkinter as ctk

from hanogtvpn.client.ui.theme import Theme
from hanogtvpn.core.constants import APP_VERSION


class ChangelogPanel(ctk.CTkScrollableFrame):
    """Scrollable panel displaying the application changelog/updates."""

    def __init__(self, parent, **kwargs):
        c = Theme.get()
        super().__init__(
            parent, fg_color=c["bg_primary"], corner_radius=0,
            scrollbar_button_color=c["scrollbar"],
            scrollbar_button_hover_color=c["text_muted"],
            **kwargs,
        )
        self._build_ui()

    def _build_ui(self):
        c = Theme.get()

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(25, 10))

        ctk.CTkLabel(
            header, text="📝  Güncellemeler / Değişiklikler",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=c["text_primary"],
        ).pack(side="left")

        # Static Data for Changelog simulating https://hanogtcodev.com format
        changelog_data = [
            {
                "version": "v0.0.1",
                "date": "Mayıs 2026",
                "title": "İlk Sürüm Yayını",
                "changes": [
                    "🚀 HanogtVPN'in tamamen yeniden yazılmış ilk modern sürümü.",
                    "🔒 AES-256-GCM uçtan uca şifreleme entegre edildi.",
                    "🔑 Perfect Forward Secrecy için ECDH anahtar değişimi eklendi.",
                    "🛡️ Sunucu doğrulaması için RSA-2048 imzaları.",
                    "🎨 Koyu ve açık tema destekli modern CustomTkinter arayüzü.",
                    "🌐 SOCKS5 Proxy özelliği eklendi (127.0.0.1:1080).",
                    "⚙️ Kill Switch, DNS Sızıntı Koruması ve Otomatik Yeniden Bağlanma özellikleri dahil edildi.",
                    "📋 Gerçek zamanlı loglama ve performans istatistikleri paneli."
                ]
            }
        ]

        # Render Changelog Cards
        for release in changelog_data:
            self._create_release_card(release)

    def _create_release_card(self, release):
        c = Theme.get()
        
        card = ctk.CTkFrame(
            self, fg_color=c["card_bg"], corner_radius=12,
            border_width=1, border_color=c["border"]
        )
        card.pack(fill="x", padx=30, pady=(10, 10))
        
        # Release Header
        header_frame = ctk.CTkFrame(card, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        version_lbl = ctk.CTkLabel(
            header_frame, text=release["version"],
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=c["accent_primary"]
        )
        version_lbl.pack(side="left")
        
        date_lbl = ctk.CTkLabel(
            header_frame, text=release["date"],
            font=ctk.CTkFont(size=12),
            text_color=c["text_muted"]
        )
        date_lbl.pack(side="right")
        
        # Release Title
        title_lbl = ctk.CTkLabel(
            card, text=release["title"],
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=c["text_primary"],
            anchor="w"
        )
        title_lbl.pack(fill="x", padx=20, pady=(0, 10))
        
        # Separator
        sep = ctk.CTkFrame(card, fg_color=c["border"], height=1)
        sep.pack(fill="x", padx=20, pady=(0, 15))
        
        # Changes List
        for change in release["changes"]:
            change_frame = ctk.CTkFrame(card, fg_color="transparent")
            change_frame.pack(fill="x", padx=20, pady=4)
            
            bullet = ctk.CTkLabel(
                change_frame, text="•",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=c["accent_primary"],
                width=15, anchor="nw"
            )
            bullet.pack(side="left", anchor="n")
            
            desc = ctk.CTkLabel(
                change_frame, text=change,
                font=ctk.CTkFont(size=13),
                text_color=c["text_secondary"],
                justify="left", anchor="w",
                wraplength=600
            )
            desc.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        # Bottom padding inside card
        ctk.CTkFrame(card, fg_color="transparent", height=10).pack()
