"""
HanogtVPN Cryptographic Engine

Provides ECDH key exchange, AES-256-GCM authenticated encryption,
RSA-2048 server authentication, and key serialisation utilities.

All cryptographic operations are backed by the ``cryptography`` library.
"""

import os
from typing import Tuple, Optional

from cryptography.hazmat.primitives.asymmetric import ec, rsa, padding, utils
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidTag, InvalidSignature

from hanogtvpn.core.constants import KEY_SIZE, NONCE_SIZE, RSA_KEY_SIZE


class CryptoEngine:
    """Handles all cryptographic operations for the VPN tunnel.

    This class is stateless — every method receives the key material it
    needs as arguments, making instances safe to share across threads.
    """

    # =================================================================
    # ECDH Key Exchange (Perfect Forward Secrecy)
    # =================================================================

    @staticmethod
    def generate_ecdh_keypair() -> Tuple[bytes, ec.EllipticCurvePrivateKey]:
        """Generate an ECDH keypair on the SECP384R1 curve.

        Returns:
            A tuple ``(public_key_bytes, private_key)`` where
            *public_key_bytes* is the uncompressed public point encoded
            as DER/SubjectPublicKeyInfo bytes.
        """
        private_key = ec.generate_private_key(ec.SECP384R1(), default_backend())
        public_key_bytes = private_key.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return public_key_bytes, private_key

    @staticmethod
    def derive_shared_secret(
        private_key: ec.EllipticCurvePrivateKey,
        peer_public_key_bytes: bytes,
    ) -> bytes:
        """Derive a symmetric key from an ECDH exchange.

        Uses HKDF-SHA256 to expand the raw shared secret into a
        *KEY_SIZE*-byte key suitable for AES-256-GCM.
        """
        peer_public_key = serialization.load_der_public_key(
            peer_public_key_bytes, default_backend()
        )
        shared_secret = private_key.exchange(ec.ECDH(), peer_public_key)

        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=None,
            info=b"hanogtvpn-session-key-v1",
            backend=default_backend(),
        ).derive(shared_secret)

        return derived_key

    # =================================================================
    # AES-256-GCM Authenticated Encryption
    # =================================================================

    @staticmethod
    def encrypt(
        plaintext: bytes,
        key: bytes,
        associated_data: Optional[bytes] = None,
    ) -> Tuple[bytes, bytes, bytes]:
        """Encrypt *plaintext* with AES-256-GCM.

        Args:
            plaintext: Data to encrypt.
            key: 32-byte AES key.
            associated_data: Optional AAD (authenticated but not encrypted).

        Returns:
            ``(nonce, ciphertext, tag)`` — the 12-byte nonce, the
            encrypted payload, and the 16-byte GCM authentication tag.
        """
        if len(key) != KEY_SIZE:
            raise ValueError(f"Key must be {KEY_SIZE} bytes, got {len(key)}")

        nonce = os.urandom(NONCE_SIZE)
        aesgcm = AESGCM(key)
        # AESGCM.encrypt returns ciphertext || tag
        ct_with_tag = aesgcm.encrypt(nonce, plaintext, associated_data)
        ciphertext = ct_with_tag[:-16]
        tag = ct_with_tag[-16:]
        return nonce, ciphertext, tag

    @staticmethod
    def decrypt(
        nonce: bytes,
        ciphertext: bytes,
        tag: bytes,
        key: bytes,
        associated_data: Optional[bytes] = None,
    ) -> bytes:
        """Decrypt AES-256-GCM *ciphertext*.

        Raises:
            ``cryptography.exceptions.InvalidTag`` if the tag verification
            fails (tampered data or wrong key).
        """
        if len(key) != KEY_SIZE:
            raise ValueError(f"Key must be {KEY_SIZE} bytes, got {len(key)}")

        aesgcm = AESGCM(key)
        ct_with_tag = ciphertext + tag
        return aesgcm.decrypt(nonce, ct_with_tag, associated_data)

    # =================================================================
    # RSA-2048 Server Authentication
    # =================================================================

    @staticmethod
    def generate_rsa_keypair() -> Tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
        """Generate an RSA-2048 keypair for server identity."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=RSA_KEY_SIZE,
            backend=default_backend(),
        )
        return private_key, private_key.public_key()

    @staticmethod
    def sign_data(private_key: rsa.RSAPrivateKey, data: bytes) -> bytes:
        """Sign *data* with an RSA private key using PSS + SHA-256."""
        return private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )

    @staticmethod
    def verify_signature(
        public_key: rsa.RSAPublicKey,
        signature: bytes,
        data: bytes,
    ) -> bool:
        """Verify an RSA-PSS signature. Returns ``True`` on success."""
        try:
            public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
        except InvalidSignature:
            return False

    # =================================================================
    # Key Serialisation
    # =================================================================

    @staticmethod
    def serialize_public_key(public_key) -> bytes:
        """Serialise a public key to PEM-encoded bytes."""
        return public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    @staticmethod
    def deserialize_public_key(key_bytes: bytes):
        """Deserialise PEM bytes to a public key object."""
        return serialization.load_pem_public_key(key_bytes, default_backend())

    @staticmethod
    def save_rsa_keys(
        private_key: rsa.RSAPrivateKey,
        public_key: rsa.RSAPublicKey,
        directory: str,
    ):
        """Save RSA keypair as PEM files in *directory*."""
        os.makedirs(directory, exist_ok=True)

        priv_path = os.path.join(directory, "server_private.pem")
        pub_path = os.path.join(directory, "server_public.pem")

        with open(priv_path, "wb") as f:
            f.write(
                private_key.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.PKCS8,
                    serialization.NoEncryption(),
                )
            )

        with open(pub_path, "wb") as f:
            f.write(
                public_key.public_bytes(
                    serialization.Encoding.PEM,
                    serialization.PublicFormat.SubjectPublicKeyInfo,
                )
            )

    @staticmethod
    def load_rsa_keys(directory: str) -> Tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
        """Load RSA keypair from PEM files in *directory*.

        Raises:
            ``FileNotFoundError`` if the key files do not exist.
        """
        priv_path = os.path.join(directory, "server_private.pem")
        pub_path = os.path.join(directory, "server_public.pem")

        with open(priv_path, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(), password=None, backend=default_backend()
            )

        with open(pub_path, "rb") as f:
            public_key = serialization.load_pem_public_key(
                f.read(), backend=default_backend()
            )

        return private_key, public_key
