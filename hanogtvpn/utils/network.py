"""
HanogtVPN Network Utilities

Helpers for IP resolution, port checking, latency measurement,
and human-readable formatting of byte counts and transfer speeds.
"""

import socket
import time
from typing import Optional


def get_local_ip() -> str:
    """Return the machine's primary local IPv4 address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def check_port_available(host: str, port: int) -> bool:
    """Return ``True`` if *port* on *host* is not already in use."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.bind((host, port))
        s.close()
        return True
    except OSError:
        return False


def measure_latency(host: str, port: int, timeout: float = 3.0) -> float:
    """Measure TCP connection latency to *host:port* in milliseconds.

    Returns ``-1.0`` on failure (unreachable / timeout).
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        start = time.perf_counter()
        s.connect((host, port))
        elapsed = (time.perf_counter() - start) * 1000.0
        s.close()
        return round(elapsed, 1)
    except OSError:
        return -1.0


def resolve_hostname(hostname: str) -> Optional[str]:
    """Resolve *hostname* to an IPv4 address string, or ``None``."""
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return None


def format_bytes(byte_count: int) -> str:
    """Format a byte count as a human-readable string (B/KB/MB/GB)."""
    if byte_count < 0:
        byte_count = 0
    if byte_count < 1024:
        return f"{byte_count} B"
    elif byte_count < 1024 ** 2:
        return f"{byte_count / 1024:.1f} KB"
    elif byte_count < 1024 ** 3:
        return f"{byte_count / 1024 ** 2:.1f} MB"
    else:
        return f"{byte_count / 1024 ** 3:.2f} GB"


def format_speed(bytes_per_sec: float) -> str:
    """Format a transfer speed as a human-readable string (/s)."""
    if bytes_per_sec < 0:
        bytes_per_sec = 0
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.0f} B/s"
    elif bytes_per_sec < 1024 ** 2:
        return f"{bytes_per_sec / 1024:.1f} KB/s"
    elif bytes_per_sec < 1024 ** 3:
        return f"{bytes_per_sec / 1024 ** 2:.1f} MB/s"
    else:
        return f"{bytes_per_sec / 1024 ** 3:.2f} GB/s"
