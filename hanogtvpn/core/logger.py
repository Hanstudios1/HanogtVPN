"""
HanogtVPN Logging System

Provides a singleton, thread-safe logger with rotating file output,
console output, and a GUI callback mechanism so the client UI can
display log entries in real-time.
"""

import logging
import os
import threading
from logging.handlers import RotatingFileHandler

from hanogtvpn.core.constants import LOG_FILE, APP_NAME


class _GUIHandler(logging.Handler):
    """Custom logging handler that forwards records to registered callbacks."""

    def __init__(self):
        super().__init__()
        self._callbacks: list = []
        self._lock_cb = threading.Lock()

    def add_callback(self, callback):
        with self._lock_cb:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def remove_callback(self, callback):
        with self._lock_cb:
            self._callbacks = [cb for cb in self._callbacks if cb is not callback]

    def emit(self, record):
        msg = self.format(record)
        with self._lock_cb:
            for cb in self._callbacks:
                try:
                    cb(record.levelname, msg)
                except Exception:
                    pass  # Never let a bad callback crash logging


class VPNLogger:
    """Singleton logger factory for HanogtVPN.

    Usage::

        logger = VPNLogger.get_logger("module_name")
        logger.info("Something happened")

        # In the GUI layer:
        VPNLogger.add_gui_handler(my_callback)
    """

    _instance = None
    _lock = threading.Lock()
    _gui_handler: _GUIHandler | None = None
    _initialised = False

    _FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-14s | %(message)s"
    _DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    @classmethod
    def _init(cls):
        """One-time initialisation of root logger, file handler, console handler."""
        if cls._initialised:
            return

        with cls._lock:
            if cls._initialised:
                return

            root = logging.getLogger(APP_NAME)
            root.setLevel(logging.DEBUG)

            formatter = logging.Formatter(cls._FORMAT, datefmt=cls._DATE_FORMAT)

            # --- Console handler ---
            console = logging.StreamHandler()
            console.setLevel(logging.INFO)
            console.setFormatter(formatter)
            root.addHandler(console)

            # --- Rotating file handler ---
            try:
                file_handler = RotatingFileHandler(
                    LOG_FILE,
                    maxBytes=5 * 1024 * 1024,  # 5 MB
                    backupCount=3,
                    encoding="utf-8",
                )
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)
                root.addHandler(file_handler)
            except OSError:
                root.warning("Could not create log file — file logging disabled")

            # --- GUI handler ---
            cls._gui_handler = _GUIHandler()
            cls._gui_handler.setLevel(logging.DEBUG)
            cls._gui_handler.setFormatter(formatter)
            root.addHandler(cls._gui_handler)

            cls._initialised = True

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Return a child logger under the ``HanogtVPN`` namespace."""
        cls._init()
        return logging.getLogger(f"{APP_NAME}.{name}")

    @classmethod
    def add_gui_handler(cls, callback):
        """Register *callback(level: str, message: str)* for GUI updates."""
        cls._init()
        if cls._gui_handler:
            cls._gui_handler.add_callback(callback)

    @classmethod
    def remove_gui_handler(cls, callback):
        """Unregister a previously added GUI callback."""
        if cls._gui_handler:
            cls._gui_handler.remove_callback(callback)

    @classmethod
    def set_level(cls, level: str):
        """Set the root logger level (DEBUG, INFO, WARNING, ERROR, CRITICAL)."""
        cls._init()
        root = logging.getLogger(APP_NAME)
        root.setLevel(getattr(logging, level.upper(), logging.INFO))
