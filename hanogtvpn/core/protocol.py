"""
HanogtVPN Wire Protocol

Defines packet framing, creation, and parsing for the VPN tunnel.

Packet format (encrypted):
    [4B length][1B type][12B nonce][ciphertext][16B GCM tag]

Packet format (unencrypted — handshake/heartbeat/disconnect):
    [4B length][1B type][payload]

Length prefix is a big-endian uint32 covering everything *after* itself
(i.e. type + nonce + ciphertext + tag, or type + payload).
"""

import json
import socket
import struct
from typing import Tuple, Optional

from hanogtvpn.core.constants import (
    HEADER_SIZE,
    PACKET_TYPE_SIZE,
    NONCE_SIZE,
    TAG_SIZE,
    PacketType,
)


class VPNProtocol:
    """Stateless helpers for packet framing and parsing."""

    # =================================================================
    # Packet creation
    # =================================================================

    @staticmethod
    def create_packet(
        packet_type: PacketType,
        payload: bytes,
        crypto_engine=None,
        session_key: bytes = None,
    ) -> bytes:
        """Create a framed packet, optionally encrypting the payload.

        If *crypto_engine* and *session_key* are provided the payload is
        encrypted with AES-256-GCM and the nonce+tag are included in the
        frame.  Otherwise the payload is sent in the clear (used for
        handshake, heartbeat, disconnect).
        """
        ptype = bytes([int(packet_type)])

        if crypto_engine is not None and session_key is not None:
            nonce, ciphertext, tag = crypto_engine.encrypt(
                payload, session_key
            )
            body = ptype + nonce + ciphertext + tag
        else:
            body = ptype + payload

        length = struct.pack("!I", len(body))
        return length + body

    # =================================================================
    # Packet parsing
    # =================================================================

    @staticmethod
    def parse_packet(
        data: bytes,
        crypto_engine=None,
        session_key: bytes = None,
    ) -> Tuple[PacketType, bytes]:
        """Parse a raw packet body (without the length prefix).

        Returns ``(packet_type, decrypted_payload)``.
        """
        if len(data) < PACKET_TYPE_SIZE:
            raise ValueError("Packet too short — no type byte")

        pkt_type = PacketType(data[0])
        rest = data[PACKET_TYPE_SIZE:]

        if crypto_engine is not None and session_key is not None:
            if len(rest) < NONCE_SIZE + TAG_SIZE:
                raise ValueError("Encrypted packet too short")
            nonce = rest[:NONCE_SIZE]
            tag = rest[-TAG_SIZE:]
            ciphertext = rest[NONCE_SIZE:-TAG_SIZE]
            payload = crypto_engine.decrypt(nonce, ciphertext, tag, session_key)
        else:
            payload = rest

        return pkt_type, payload

    # =================================================================
    # Socket-level receiving
    # =================================================================

    @staticmethod
    def recv_exact(sock: socket.socket, n: int) -> bytes:
        """Receive exactly *n* bytes from *sock*.

        Raises ``ConnectionError`` if the peer closes the connection
        before all bytes are received.
        """
        chunks = []
        remaining = n
        while remaining > 0:
            chunk = sock.recv(min(remaining, 65536))
            if not chunk:
                raise ConnectionError("Connection closed while receiving data")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    @staticmethod
    def recv_packet(
        sock: socket.socket,
        crypto_engine=None,
        session_key: bytes = None,
    ) -> Tuple[Optional[PacketType], Optional[bytes]]:
        """Read exactly one complete packet from *sock*.

        Returns ``(packet_type, payload)`` or ``(None, None)`` if the
        connection was closed cleanly.
        """
        try:
            header = VPNProtocol.recv_exact(sock, HEADER_SIZE)
        except ConnectionError:
            return None, None

        (body_len,) = struct.unpack("!I", header)

        if body_len == 0:
            return None, None
        if body_len > 10 * 1024 * 1024:  # 10 MB sanity limit
            raise ValueError(f"Packet too large: {body_len} bytes")

        body = VPNProtocol.recv_exact(sock, body_len)
        return VPNProtocol.parse_packet(body, crypto_engine, session_key)

    # =================================================================
    # Handshake helpers
    # =================================================================

    @staticmethod
    def create_handshake_request(ecdh_public_key: bytes) -> bytes:
        """Create a HANDSHAKE_REQUEST carrying the client's ECDH public key."""
        return VPNProtocol.create_packet(
            PacketType.HANDSHAKE_REQUEST, ecdh_public_key
        )

    @staticmethod
    def create_handshake_response(
        ecdh_public_key: bytes,
        rsa_signature: bytes,
        server_public_key_pem: bytes,
    ) -> bytes:
        """Create a HANDSHAKE_RESPONSE with ECDH key, RSA signature, and
        server certificate (PEM).

        The payload is a JSON object with base64-free length-prefixed
        binary fields for efficiency.
        """
        # Simple TLV-ish encoding:
        #   [4B ecdh_len][ecdh_pub][4B sig_len][signature][rest = pem]
        payload = (
            struct.pack("!I", len(ecdh_public_key))
            + ecdh_public_key
            + struct.pack("!I", len(rsa_signature))
            + rsa_signature
            + server_public_key_pem
        )
        return VPNProtocol.create_packet(PacketType.HANDSHAKE_RESPONSE, payload)

    @staticmethod
    def parse_handshake_response(payload: bytes) -> dict:
        """Parse a HANDSHAKE_RESPONSE payload into components.

        Returns a dict with keys ``ecdh_public_key``, ``rsa_signature``,
        ``server_public_key_pem``.
        """
        offset = 0

        (ecdh_len,) = struct.unpack_from("!I", payload, offset)
        offset += 4
        ecdh_pub = payload[offset : offset + ecdh_len]
        offset += ecdh_len

        (sig_len,) = struct.unpack_from("!I", payload, offset)
        offset += 4
        rsa_sig = payload[offset : offset + sig_len]
        offset += sig_len

        server_pem = payload[offset:]

        return {
            "ecdh_public_key": ecdh_pub,
            "rsa_signature": rsa_sig,
            "server_public_key_pem": server_pem,
        }

    # =================================================================
    # Utility packets
    # =================================================================

    @staticmethod
    def create_heartbeat() -> bytes:
        """Create a HEARTBEAT packet (empty payload)."""
        return VPNProtocol.create_packet(PacketType.HEARTBEAT, b"")

    @staticmethod
    def create_disconnect() -> bytes:
        """Create a DISCONNECT packet (empty payload)."""
        return VPNProtocol.create_packet(PacketType.DISCONNECT, b"")
