"""
HanogtVPN Settings Manager

Thread-safe JSON-backed settings with defaults and validation.
"""

import json
import os
import threading

from hanogtvpn.core.constants import SETTINGS_FILE, DEFAULT_PORT


_DEFAULTS = {
    "ip": "127.0.0.1",
    "port": DEFAULT_PORT,
    "encryption": "AES-256-GCM",
    "protocol": "TCP",
    "kill_switch": False,
    "auto_start": False,
    "auto_reconnect": True,
    "dns_leak_protection": True,
    "theme": "Dark",
    "selected_server_index": 0,
    "log_level": "INFO",
}


class SettingsManager:
    """Manages VPN client settings with JSON persistence."""

    def __init__(self, path: str = SETTINGS_FILE):
        self._path = path
        self._lock = threading.Lock()
        self._settings: dict = self._load()

    # --- public API ---------------------------------------------------

    @property
    def data(self) -> dict:
        """Return a *copy* of the current settings."""
        with self._lock:
            return self._settings.copy()

    def get(self, key: str, default=None):
        with self._lock:
            return self._settings.get(key, default)

    def set(self, key: str, value):
        with self._lock:
            self._settings[key] = value
            self._save()

    def update(self, **kwargs):
        with self._lock:
            self._settings.update(kwargs)
            self._save()

    def reset(self):
        with self._lock:
            self._settings = _DEFAULTS.copy()
            self._save()

    # --- internal -----------------------------------------------------

    def _load(self) -> dict:
        if not os.path.exists(self._path):
            settings = _DEFAULTS.copy()
            self._save_dict(settings)
            return settings
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            # Merge with defaults so new keys are always present
            merged = _DEFAULTS.copy()
            merged.update(loaded)
            return merged
        except (json.JSONDecodeError, OSError):
            return _DEFAULTS.copy()

    def _save(self):
        self._save_dict(self._settings)

    def _save_dict(self, d: dict):
        try:
            tmp = self._path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(d, f, indent=4, ensure_ascii=False)
            # Atomic replace (Windows: os.replace is atomic)
            os.replace(tmp, self._path)
        except OSError:
            pass
