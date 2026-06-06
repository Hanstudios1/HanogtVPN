"""
HanogtVPN Client Application

Main window with sidebar navigation, panel switching, status bar,
and connection lifecycle management.
"""

import customtkinter as ctk
import sys
import os
from PIL import Image

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

from hanogtvpn.client.ui.theme import Theme
from hanogtvpn.client.ui.main_panel import MainPanel
from hanogtvpn.client.ui.settings_panel import SettingsPanel
from hanogtvpn.client.ui.logs_panel import LogsPanel
from hanogtvpn.client.ui.server_list import ServerListPanel
from hanogtvpn.client.ui.changelog_panel import ChangelogPanel
from hanogtvpn.client.settings import SettingsManager
from hanogtvpn.client.connection import ConnectionManager
from hanogtvpn.core.constants import ConnectionState, DEFAULT_SERVERS, APP_VERSION
from hanogtvpn.core.logger import VPNLogger
from hanogtvpn.utils.network import format_bytes, format_speed

# Initialise CTk appearance before any widget creation
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class HanogtVPNApp(ctk.CTk):
    """Main HanogtVPN client window."""

    def __init__(self):
        super().__init__()

        # Settings
        self.settings = SettingsManager()
        self._theme_mode = self.settings.get("theme", "Dark")
        Theme.set_theme(self._theme_mode)
        ctk.set_appearance_mode(self._theme_mode)

        self.logger = VPNLogger.get_logger("app")
        VPNLogger.set_level(self.settings.get("log_level", "INFO"))

        # Connection manager
        self.conn = ConnectionManager(root_window=self)

        # Window config
        c = Theme.get()
        self.title("HanogtVPN")
        self.geometry("920x640")
        self.minsize(920, 640)
        self.resizable(False, False)
        self.configure(fg_color=c["bg_primary"])
        
        # Set Window Icon
        try:
            self.iconbitmap(resource_path("hanogtvpn/client/assets/logo.ico"))
        except Exception as e:
            self.logger.warning(f"Could not load window icon: {e}")

        # Track active panel
        self._active_panel = "main"
        self._nav_buttons: dict[str, ctk.CTkButton] = {}

        self._build_ui()
        self._show_panel("main")

        # Window close handler
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.logger.info("HanogtVPN Client started")

    def _build_ui(self):
        c = Theme.get()

        # === Sidebar ==================================================
        self.sidebar = ctk.CTkFrame(
            self, width=210, corner_radius=0,
            fg_color=c["sidebar_bg"],
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=20, pady=(30, 5))

        # Logo Image
        try:
            logo_img = ctk.CTkImage(
                light_image=Image.open(resource_path("hanogtvpn/client/assets/logo.png")),
                dark_image=Image.open(resource_path("hanogtvpn/client/assets/logo.png")),
                size=(64, 64)
            )
            ctk.CTkLabel(logo_frame, text="", image=logo_img).pack()
        except Exception:
            ctk.CTkLabel(logo_frame, text="🛡️", font=ctk.CTkFont(size=32)).pack()

        ctk.CTkLabel(
            logo_frame, text="HanogtVPN",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=c["text_primary"],
        ).pack(pady=(5, 0))

        ctk.CTkLabel(
            logo_frame, text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=11),
            text_color=c["text_muted"],
        ).pack()

        # Separator
        sep = ctk.CTkFrame(self.sidebar, fg_color=c["border"], height=1)
        sep.pack(fill="x", padx=20, pady=20)

        # Navigation
        nav_items = [
            ("main", "🏠  Ana Ekran"),
            ("servers", "🌐  Sunucular"),
            ("settings", "⚙️  Ayarlar"),
            ("changelog", "📝  Güncellemeler"),
            ("logs", "📋  Loglar"),
        ]

        for key, label in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                fg_color="transparent",
                text_color=c["text_secondary"],
                hover_color=c["sidebar_active"],
                anchor="w",
                corner_radius=10,
                height=42,
                font=ctk.CTkFont(size=14),
                command=lambda k=key: self._show_panel(k),
            )
            btn.pack(fill="x", padx=12, pady=2)
            self._nav_buttons[key] = btn

        # Spacer
        ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(fill="both", expand=True)

        # Theme toggle
        theme_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        theme_frame.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(
            theme_frame, text="Tema",
            font=ctk.CTkFont(size=12),
            text_color=c["text_muted"],
        ).pack(anchor="w", padx=5, pady=(0, 5))

        self.theme_btn = ctk.CTkSegmentedButton(
            theme_frame,
            values=["Koyu", "Açık"],
            command=self._on_theme_change,
            selected_color=c["accent_secondary"],
            selected_hover_color=c["button_primary_hover"],
            unselected_color=c["bg_tertiary"],
            unselected_hover_color=c["bg_hover"],
            text_color=c["text_primary"],
            font=ctk.CTkFont(size=12),
            corner_radius=8,
        )
        self.theme_btn.set("Koyu" if self._theme_mode == "Dark" else "Açık")
        self.theme_btn.pack(fill="x", padx=5)

        # Connection status in sidebar
        self.sidebar_status = ctk.CTkLabel(
            self.sidebar, text="⬤ Bağlı Değil",
            font=ctk.CTkFont(size=12),
            text_color=c["accent_danger"],
        )
        self.sidebar_status.pack(pady=(10, 20))

        # === Content Area =============================================
        self.content = ctk.CTkFrame(self, fg_color=c["bg_primary"], corner_radius=0)
        self.content.pack(side="right", fill="both", expand=True)

        # Create panels
        self.main_panel = MainPanel(
            self.content, self.conn, self.settings
        )
        self.server_panel = ServerListPanel(
            self.content, self.settings,
            on_server_select=self._on_server_select,
        )
        self.settings_panel = SettingsPanel(self.content, self.settings)
        self.changelog_panel = ChangelogPanel(self.content)
        self.logs_panel = LogsPanel(self.content)

        self._panels = {
            "main": self.main_panel,
            "servers": self.server_panel,
            "settings": self.settings_panel,
            "changelog": self.changelog_panel,
            "logs": self.logs_panel,
        }

        # Set initial server info
        idx = self.settings.get("selected_server_index", 0)
        if 0 <= idx < len(DEFAULT_SERVERS):
            self.main_panel.update_server_info(DEFAULT_SERVERS[idx])

        # Register state callback for sidebar
        self.conn.add_state_callback(self._on_connection_state)

        # === Status Bar ===============================================
        self.status_bar = ctk.CTkFrame(
            self, fg_color=c["sidebar_bg"], height=32, corner_radius=0,
        )
        self.status_bar.pack(side="bottom", fill="x")
        self.status_bar.pack_propagate(False)

        self.statusbar_label = ctk.CTkLabel(
            self.status_bar,
            text=f"HanogtVPN v{APP_VERSION}  •  Hazır",
            font=ctk.CTkFont(size=11),
            text_color=c["text_muted"],
        )
        self.statusbar_label.pack(side="left", padx=15)

        self.statusbar_speed = ctk.CTkLabel(
            self.status_bar, text="",
            font=ctk.CTkFont(size=11),
            text_color=c["text_muted"],
        )
        self.statusbar_speed.pack(side="right", padx=15)

        # Register stats callback for status bar
        self.conn.add_stats_callback(self._on_statusbar_stats)

    # === Panel Navigation =============================================

    def _show_panel(self, panel_key: str):
        c = Theme.get()

        # Hide all panels
        for p in self._panels.values():
            p.pack_forget()

        # Show selected panel
        self._panels[panel_key].pack(fill="both", expand=True)
        self._active_panel = panel_key

        # Update nav button styles
        for key, btn in self._nav_buttons.items():
            if key == panel_key:
                btn.configure(
                    fg_color=c["sidebar_active"],
                    text_color=c["accent_primary"],
                    font=ctk.CTkFont(size=14, weight="bold"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=c["text_secondary"],
                    font=ctk.CTkFont(size=14),
                )

    # === Callbacks ====================================================

    def _on_server_select(self, server: dict):
        self.main_panel.update_server_info(server)
        self._show_panel("main")

    def _on_connection_state(self, state: ConnectionState):
        c = Theme.get()
        if state == ConnectionState.DISCONNECTED:
            self.sidebar_status.configure(
                text="⬤ Bağlı Değil", text_color=c["accent_danger"]
            )
            self.statusbar_label.configure(text=f"HanogtVPN v{APP_VERSION}  •  Hazır")
        elif state == ConnectionState.CONNECTING:
            self.sidebar_status.configure(
                text="⬤ Bağlanıyor...", text_color=c["accent_warning"]
            )
            self.statusbar_label.configure(text=f"HanogtVPN v{APP_VERSION}  •  Bağlanıyor...")
        elif state == ConnectionState.CONNECTED:
            self.sidebar_status.configure(
                text="⬤ Bağlı", text_color=c["success"]
            )
            self.statusbar_label.configure(text=f"HanogtVPN v{APP_VERSION}  •  Bağlı")
        elif state == ConnectionState.ERROR:
            self.sidebar_status.configure(
                text="⬤ Hata", text_color=c["accent_danger"]
            )
            self.statusbar_label.configure(text=f"HanogtVPN v{APP_VERSION}  •  Bağlantı Hatası")

    def _on_statusbar_stats(self, stats: dict):
        if stats["state"] == ConnectionState.CONNECTED:
            up = format_speed(stats["upload_speed"])
            down = format_speed(stats["download_speed"])
            self.statusbar_speed.configure(text=f"↑ {up}  ↓ {down}")
        else:
            self.statusbar_speed.configure(text="")

    def _on_theme_change(self, value: str):
        mode = "Dark" if value == "Koyu" else "Light"
        Theme.set_theme(mode)
        ctk.set_appearance_mode(mode)
        self.settings.set("theme", mode)
        # Note: full theme colour refresh requires restart for card colours

    def _on_close(self):
        """Handle window close — disconnect and exit."""
        if self.conn.state == ConnectionState.CONNECTED:
            self.conn.disconnect()
        self.logger.info("HanogtVPN Client closed")
        self.destroy()
        sys.exit(0)


def main():
    app = HanogtVPNApp()
    app.mainloop()


if __name__ == "__main__":
    main()
