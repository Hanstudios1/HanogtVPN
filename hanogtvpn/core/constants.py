"""
HanogtVPN Constants Module
--------------------------
Defines all constants, enumerations, and default configuration values
used across the HanogtVPN application.
"""

import os
from enum import IntEnum, Enum


# =============================================================================
# Application Metadata
# =============================================================================
APP_NAME: str = "HanogtVPN"
APP_VERSION: str = "0.0.1"

# =============================================================================
# Network Defaults
# =============================================================================
DEFAULT_PORT: int = 9999
BUFFER_SIZE: int = 65536

# =============================================================================
# Packet Framing
# =============================================================================
HEADER_SIZE: int = 4          # 4-byte length prefix (big-endian uint32)
PACKET_TYPE_SIZE: int = 1     # 1-byte packet type identifier

# =============================================================================
# Cryptographic Parameters
# =============================================================================
NONCE_SIZE: int = 12          # AES-GCM nonce (96 bits)
TAG_SIZE: int = 16            # AES-GCM authentication tag (128 bits)
KEY_SIZE: int = 32            # AES-256 key (256 bits)
RSA_KEY_SIZE: int = 2048      # RSA key size in bits

# =============================================================================
# Timing & Connection
# =============================================================================
HEARTBEAT_INTERVAL: int = 15          # Seconds between heartbeats
CONNECTION_TIMEOUT: int = 10          # Socket connection timeout in seconds
MAX_RECONNECT_ATTEMPTS: int = 5       # Maximum reconnection retries
RECONNECT_DELAY: int = 3              # Seconds between reconnection attempts


# =============================================================================
# Packet Types (Wire Protocol)
# =============================================================================
class PacketType(IntEnum):
    """Defines the types of packets exchanged over the VPN tunnel."""
    HANDSHAKE_REQUEST = 0x01
    HANDSHAKE_RESPONSE = 0x02
    DATA = 0x03
    HEARTBEAT = 0x04
    DISCONNECT = 0x05
    ERROR = 0x06


# =============================================================================
# Encryption Types
# =============================================================================
class EncryptionType(Enum):
    """Supported encryption algorithms."""
    AES_256_GCM = "AES-256-GCM"
    AES_128_GCM = "AES-128-GCM"
    NONE = "NONE"


# =============================================================================
# Protocol Types
# =============================================================================
class ProtocolType(Enum):
    """Supported transport protocols."""
    TCP = "TCP"
    UDP = "UDP"


# =============================================================================
# Connection States
# =============================================================================
class ConnectionState(Enum):
    """Represents the current state of a VPN connection."""
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    DISCONNECTING = "DISCONNECTING"
    ERROR = "ERROR"


# =============================================================================
# Default Server List
# =============================================================================
DEFAULT_SERVERS: list[dict] = [
    {
        "name": "İstanbul",
        "host": "127.0.0.1",
        "port": 9999,
        "country": "Türkiye",
        "flag_emoji": "🇹🇷",
    },
    {
        "name": "Frankfurt",
        "host": "127.0.0.1",
        "port": 9998,
        "country": "Almanya",
        "flag_emoji": "🇩🇪",
    },
    {
        "name": "Amsterdam",
        "host": "127.0.0.1",
        "port": 9997,
        "country": "Hollanda",
        "flag_emoji": "🇳🇱",
    },
    {
        "name": "Londra",
        "host": "127.0.0.1",
        "port": 9996,
        "country": "İngiltere",
        "flag_emoji": "🇬🇧",
    },
    {
        "name": "New York",
        "host": "127.0.0.1",
        "port": 9995,
        "country": "ABD",
        "flag_emoji": "🇺🇸",
    },
]


# =============================================================================
# File Paths
# =============================================================================
SETTINGS_FILE: str = "hanogtvpn_settings.json"
LOG_FILE: str = "hanogtvpn.log"
KEYS_DIRECTORY: str = os.path.join("keys", "")
