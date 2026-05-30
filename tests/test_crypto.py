"""
Comprehensive tests for the HanogtVPN CryptoEngine.
"""

import os
import unittest

from hanogtvpn.core.crypto import CryptoEngine
from hanogtvpn.core.constants import KEY_SIZE, NONCE_SIZE


class TestECDH(unittest.TestCase):
    """Test ECDH key exchange and shared secret derivation."""

    def setUp(self):
        self.crypto = CryptoEngine()

    def test_generate_ecdh_keypair(self):
        pub_bytes, priv_key = self.crypto.generate_ecdh_keypair()
        self.assertIsInstance(pub_bytes, bytes)
        self.assertGreater(len(pub_bytes), 0)
        self.assertIsNotNone(priv_key)

    def test_ecdh_key_exchange(self):
        """Both sides derive the same shared secret."""
        pub_a, priv_a = self.crypto.generate_ecdh_keypair()
        pub_b, priv_b = self.crypto.generate_ecdh_keypair()

        secret_a = self.crypto.derive_shared_secret(priv_a, pub_b)
        secret_b = self.crypto.derive_shared_secret(priv_b, pub_a)

        self.assertEqual(secret_a, secret_b)
        self.assertEqual(len(secret_a), KEY_SIZE)

    def test_different_keypairs_different_secrets(self):
        """Different keypair combinations yield different secrets."""
        pub_a, priv_a = self.crypto.generate_ecdh_keypair()
        pub_b, priv_b = self.crypto.generate_ecdh_keypair()
        pub_c, priv_c = self.crypto.generate_ecdh_keypair()

        secret_ab = self.crypto.derive_shared_secret(priv_a, pub_b)
        secret_ac = self.crypto.derive_shared_secret(priv_a, pub_c)

        self.assertNotEqual(secret_ab, secret_ac)


class TestAESGCM(unittest.TestCase):
    """Test AES-256-GCM encryption and decryption."""

    def setUp(self):
        self.crypto = CryptoEngine()
        self.key = os.urandom(KEY_SIZE)

    def test_encrypt_decrypt(self):
        plaintext = b"Hello, HanogtVPN! This is a test message."
        nonce, ciphertext, tag = self.crypto.encrypt(plaintext, self.key)

        self.assertEqual(len(nonce), NONCE_SIZE)
        self.assertEqual(len(tag), 16)
        self.assertNotEqual(ciphertext, plaintext)

        decrypted = self.crypto.decrypt(nonce, ciphertext, tag, self.key)
        self.assertEqual(decrypted, plaintext)

    def test_encrypt_decrypt_with_aad(self):
        plaintext = b"Secret data"
        aad = b"additional-auth-data"
        nonce, ct, tag = self.crypto.encrypt(plaintext, self.key, aad)
        result = self.crypto.decrypt(nonce, ct, tag, self.key, aad)
        self.assertEqual(result, plaintext)

    def test_wrong_key_fails(self):
        plaintext = b"Sensitive information"
        nonce, ct, tag = self.crypto.encrypt(plaintext, self.key)

        wrong_key = os.urandom(KEY_SIZE)
        with self.assertRaises(Exception):
            self.crypto.decrypt(nonce, ct, tag, wrong_key)

    def test_tampered_ciphertext_fails(self):
        plaintext = b"Do not tamper with this"
        nonce, ct, tag = self.crypto.encrypt(plaintext, self.key)

        tampered = bytearray(ct)
        if len(tampered) > 0:
            tampered[0] ^= 0xFF
        with self.assertRaises(Exception):
            self.crypto.decrypt(nonce, bytes(tampered), tag, self.key)

    def test_tampered_tag_fails(self):
        plaintext = b"Tag integrity check"
        nonce, ct, tag = self.crypto.encrypt(plaintext, self.key)

        bad_tag = bytearray(tag)
        bad_tag[0] ^= 0xFF
        with self.assertRaises(Exception):
            self.crypto.decrypt(nonce, ct, bytes(bad_tag), self.key)

    def test_nonce_uniqueness(self):
        """Each encryption should produce a unique nonce."""
        plaintext = b"Same message"
        nonces = set()
        for _ in range(100):
            nonce, _, _ = self.crypto.encrypt(plaintext, self.key)
            nonces.add(nonce)
        self.assertEqual(len(nonces), 100)

    def test_empty_plaintext(self):
        nonce, ct, tag = self.crypto.encrypt(b"", self.key)
        result = self.crypto.decrypt(nonce, ct, tag, self.key)
        self.assertEqual(result, b"")

    def test_large_plaintext(self):
        plaintext = os.urandom(1024 * 1024)  # 1 MB
        nonce, ct, tag = self.crypto.encrypt(plaintext, self.key)
        result = self.crypto.decrypt(nonce, ct, tag, self.key)
        self.assertEqual(result, plaintext)

    def test_invalid_key_size(self):
        with self.assertRaises(ValueError):
            self.crypto.encrypt(b"test", b"short_key")


class TestRSA(unittest.TestCase):
    """Test RSA signing, verification, and serialisation."""

    def setUp(self):
        self.crypto = CryptoEngine()
        self.private_key, self.public_key = self.crypto.generate_rsa_keypair()

    def test_sign_and_verify(self):
        data = b"Data to sign for authentication"
        signature = self.crypto.sign_data(self.private_key, data)
        self.assertIsInstance(signature, bytes)
        self.assertGreater(len(signature), 0)

        result = self.crypto.verify_signature(self.public_key, signature, data)
        self.assertTrue(result)

    def test_wrong_signature_fails(self):
        data = b"Original data"
        signature = self.crypto.sign_data(self.private_key, data)

        bad_sig = bytearray(signature)
        bad_sig[0] ^= 0xFF

        result = self.crypto.verify_signature(
            self.public_key, bytes(bad_sig), data
        )
        self.assertFalse(result)

    def test_wrong_data_fails(self):
        data = b"Original data"
        signature = self.crypto.sign_data(self.private_key, data)

        result = self.crypto.verify_signature(
            self.public_key, signature, b"Tampered data"
        )
        self.assertFalse(result)

    def test_key_serialization(self):
        pem = self.crypto.serialize_public_key(self.public_key)
        self.assertIn(b"BEGIN PUBLIC KEY", pem)

        restored = self.crypto.deserialize_public_key(pem)
        pem2 = self.crypto.serialize_public_key(restored)
        self.assertEqual(pem, pem2)

    def test_save_and_load_keys(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            self.crypto.save_rsa_keys(
                self.private_key, self.public_key, tmpdir
            )

            loaded_priv, loaded_pub = self.crypto.load_rsa_keys(tmpdir)

            # Verify the loaded keys work
            data = b"Round-trip test"
            sig = self.crypto.sign_data(loaded_priv, data)
            self.assertTrue(
                self.crypto.verify_signature(loaded_pub, sig, data)
            )


if __name__ == "__main__":
    unittest.main()
