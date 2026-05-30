"""
HanogtVPN Theme Manager

Centralised colour palette and theme switching for the CustomTkinter GUI.
"""


class Theme:
    """Provides colour tokens for the HanogtVPN dark and light themes."""

    # === Dark theme (default) =========================================
    DARK = {
        "bg_primary": "#0A0A0F",
        "bg_secondary": "#12121A",
        "bg_tertiary": "#1A1A2E",
        "bg_hover": "#222238",
        "accent_primary": "#00D4AA",
        "accent_secondary": "#7C3AED",
        "accent_danger": "#EF4444",
        "accent_warning": "#F59E0B",
        "text_primary": "#F1F5F9",
        "text_secondary": "#94A3B8",
        "text_muted": "#475569",
        "border": "#1E293B",
        "success": "#10B981",
        "card_bg": "#12121A",
        "sidebar_bg": "#0E0E16",
        "sidebar_active": "#1A1A2E",
        "button_primary": "#7C3AED",
        "button_primary_hover": "#6D28D9",
        "button_connect": "#00D4AA",
        "button_connect_hover": "#00B894",
        "button_disconnect": "#EF4444",
        "button_disconnect_hover": "#DC2626",
        "button_connecting": "#F59E0B",
        "scrollbar": "#1E293B",
        "input_bg": "#1A1A2E",
        "input_border": "#2D2D44",
    }

    # === Light theme ===================================================
    LIGHT = {
        "bg_primary": "#F8FAFC",
        "bg_secondary": "#FFFFFF",
        "bg_tertiary": "#F1F5F9",
        "bg_hover": "#E2E8F0",
        "accent_primary": "#059669",
        "accent_secondary": "#7C3AED",
        "accent_danger": "#DC2626",
        "accent_warning": "#D97706",
        "text_primary": "#0F172A",
        "text_secondary": "#475569",
        "text_muted": "#94A3B8",
        "border": "#E2E8F0",
        "success": "#059669",
        "card_bg": "#FFFFFF",
        "sidebar_bg": "#F1F5F9",
        "sidebar_active": "#E2E8F0",
        "button_primary": "#7C3AED",
        "button_primary_hover": "#6D28D9",
        "button_connect": "#059669",
        "button_connect_hover": "#047857",
        "button_disconnect": "#DC2626",
        "button_disconnect_hover": "#B91C1C",
        "button_connecting": "#D97706",
        "scrollbar": "#CBD5E1",
        "input_bg": "#F1F5F9",
        "input_border": "#CBD5E1",
    }

    _current = "Dark"

    @classmethod
    def get(cls) -> dict:
        """Return the active colour palette dict."""
        return cls.DARK if cls._current == "Dark" else cls.LIGHT

    @classmethod
    def set_theme(cls, mode: str):
        """Switch theme. *mode* must be ``'Dark'`` or ``'Light'``."""
        cls._current = mode if mode in ("Dark", "Light") else "Dark"

    @classmethod
    def current(cls) -> str:
        return cls._current

    # Convenience aliases
    @classmethod
    def is_dark(cls) -> bool:
        return cls._current == "Dark"
