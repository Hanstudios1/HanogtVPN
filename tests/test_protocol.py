"""
Tests for the HanogtVPN wire protocol.
"""

import os
import unittest

from hanogtvpn.core.protocol import VPNProtocol
from hanogtvpn.core.crypto import CryptoEngine
from hanogtvpn.core.constants import PacketType, KEY_SIZE


class TestPacketCreationAndParsing(unittest.TestCase):
    """Test packet framing and parsing without encryption."""

    def test_create_parse_unencrypted(self):
        payload = b"Hello VPN"
        pkt = VPNProtocol.create_packet(PacketType.DATA, payload)
        self.assertIsInstance(pkt, bytes)
        self.assertGreater(len(pkt), len(payload))

        # Skip the 4-byte length prefix to parse
        body = pkt[4:]
        pkt_type, parsed = VPNProtocol.parse_packet(body)
        self.assertEqual(pkt_type, PacketType.DATA)
        self.assertEqual(parsed, payload)

    def test_create_parse_encrypted(self):
        crypto = CryptoEngine()
        key = os.urandom(KEY_SIZE)
        payload = b"Encrypted tunnel data"

        pkt = VPNProtocol.create_packet(PacketType.DATA, payload, crypto, key)
        body = pkt[4:]

        pkt_type, decrypted = VPNProtocol.parse_packet(body, crypto, key)
        self.assertEqual(pkt_type, PacketType.DATA)
        self.assertEqual(decrypted, payload)

    def test_all_packet_types(self):
        for pt in PacketType:
            pkt = VPNProtocol.create_packet(pt, b"test")
            body = pkt[4:]
            parsed_type, parsed_payload = VPNProtocol.parse_packet(body)
            self.assertEqual(parsed_type, pt)
            self.assertEqual(parsed_payload, b"test")

    def test_empty_payload(self):
        pkt = VPNProtocol.create_packet(PacketType.HEARTBEAT, b"")
        body = pkt[4:]
        pkt_type, payload = VPNProtocol.parse_packet(body)
        self.assertEqual(pkt_type, PacketType.HEARTBEAT)
        self.assertEqual(payload, b"")

    def test_large_payload(self):
        data = os.urandom(100_000)
        pkt = VPNProtocol.create_packet(PacketType.DATA, data)
        body = pkt[4:]
        pkt_type, payload = VPNProtocol.parse_packet(body)
        self.assertEqual(payload, data)


class TestHandshakeProtocol(unittest.TestCase):
    """Test handshake packet creation and parsing."""

    def setUp(self):
        self.crypto = CryptoEngine()

    def test_handshake_request(self):
        pub_bytes, _ = self.crypto.generate_ecdh_keypair()
        pkt = VPNProtocol.create_handshake_request(pub_bytes)
        body = pkt[4:]
        pkt_type, payload = VPNProtocol.parse_packet(body)
        self.assertEqual(pkt_type, PacketType.HANDSHAKE_REQUEST)
        self.assertEqual(payload, pub_bytes)

    def test_handshake_response_roundtrip(self):
        ecdh_pub, _ = self.crypto.generate_ecdh_keypair()
        priv_key, pub_key = self.crypto.generate_rsa_keypair()
        signature = self.crypto.sign_data(priv_key, ecdh_pub)
        server_pem = self.crypto.serialize_public_key(pub_key)

        pkt = VPNProtocol.create_handshake_response(
            ecdh_pub, signature, server_pem
        )
        body = pkt[4:]
        pkt_type, payload = VPNProtocol.parse_packet(body)
        self.assertEqual(pkt_type, PacketType.HANDSHAKE_RESPONSE)

        parsed = VPNProtocol.parse_handshake_response(payload)
        self.assertEqual(parsed["ecdh_public_key"], ecdh_pub)
        self.assertEqual(parsed["rsa_signature"], signature)
        self.assertEqual(parsed["server_public_key_pem"], server_pem)

    def test_heartbeat_packet(self):
        pkt = VPNProtocol.create_heartbeat()
        body = pkt[4:]
        pkt_type, payload = VPNProtocol.parse_packet(body)
        self.assertEqual(pkt_type, PacketType.HEARTBEAT)
        self.assertEqual(payload, b"")

    def test_disconnect_packet(self):
        pkt = VPNProtocol.create_disconnect()
        body = pkt[4:]
        pkt_type, payload = VPNProtocol.parse_packet(body)
        self.assertEqual(pkt_type, PacketType.DISCONNECT)
        self.assertEqual(payload, b"")


class TestEncryptedIntegrity(unittest.TestCase):
    """Verify encrypted packets cannot be tampered with."""

    def test_tampered_encrypted_packet_fails(self):
        crypto = CryptoEngine()
        key = os.urandom(KEY_SIZE)

        pkt = VPNProtocol.create_packet(
            PacketType.DATA, b"secure data", crypto, key
        )
        # Tamper with a byte in the encrypted body
        pkt_bytes = bytearray(pkt)
        if len(pkt_bytes) > 10:
            pkt_bytes[10] ^= 0xFF

        body = bytes(pkt_bytes[4:])
        with self.assertRaises(Exception):
            VPNProtocol.parse_packet(body, crypto, key)


if __name__ == "__main__":
    unittest.main()
