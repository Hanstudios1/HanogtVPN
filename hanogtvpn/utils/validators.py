"""
HanogtVPN Input Validators

Functions for validating and sanitising user-supplied network parameters.
"""

import re
import ipaddress


def validate_ip(ip: str) -> bool:
    """Return ``True`` if *ip* is a valid IPv4 address."""
    try:
        ipaddress.IPv4Address(ip.strip())
        return True
    except (ipaddress.AddressValueError, ValueError):
        return False


def validate_port(port) -> bool:
    """Return ``True`` if *port* is a valid TCP/UDP port (1–65535)."""
    try:
        p = int(port)
        return 1 <= p <= 65535
    except (TypeError, ValueError):
        return False


def validate_hostname(hostname: str) -> bool:
    """Return ``True`` if *hostname* is a syntactically valid DNS hostname."""
    if not hostname or len(hostname) > 253:
        return False
    pattern = re.compile(
        r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*$"
    )
    return bool(pattern.match(hostname.strip()))


def sanitize_input(text: str) -> str:
    """Remove potentially dangerous characters from user input."""
    if not isinstance(text, str):
        return ""
    # Strip control characters, null bytes, and common injection chars
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    cleaned = cleaned.replace("\r", "").strip()
    return cleaned
