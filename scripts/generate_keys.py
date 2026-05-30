#!/usr/bin/env python3
"""
RSA Key Pair Generator for HanogtVPN Server

Generates an RSA-2048 keypair and saves it to the keys/ directory.
These keys are used for server identity verification during the
ECDH handshake.
"""

import os
import sys
import hashlib

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hanogtvpn.core.crypto import CryptoEngine


def get_key_fingerprint(public_key_pem: bytes) -> str:
    """Compute SHA-256 fingerprint of a public key."""
    digest = hashlib.sha256(public_key_pem).hexdigest()
    # Format as colon-separated pairs
    return ":".join(digest[i:i+2] for i in range(0, len(digest), 2))


def main():
    keys_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "keys",
    )
    os.makedirs(keys_dir, exist_ok=True)

    priv_path = os.path.join(keys_dir, "server_private.pem")
    pub_path = os.path.join(keys_dir, "server_public.pem")

    # Check for existing keys
    if os.path.exists(priv_path) or os.path.exists(pub_path):
        print("⚠️  Mevcut RSA anahtarları bulundu!")
        print(f"   Konum: {keys_dir}")
        answer = input("   Üzerine yazılsın mı? (e/h): ").strip().lower()
        if answer not in ("e", "evet", "y", "yes"):
            print("❌ İptal edildi.")
            return

    print("🔑 RSA-2048 anahtar çifti oluşturuluyor...")
    crypto = CryptoEngine()
    private_key, public_key = crypto.generate_rsa_keypair()
    crypto.save_rsa_keys(private_key, public_key, keys_dir)

    # Show fingerprint
    pub_pem = crypto.serialize_public_key(public_key)
    fingerprint = get_key_fingerprint(pub_pem)

    print()
    print("✅ Anahtarlar başarıyla oluşturuldu!")
    print(f"   📁 Konum: {keys_dir}")
    print(f"   🔒 Özel anahtar: server_private.pem")
    print(f"   🔓 Genel anahtar: server_public.pem")
    print(f"   🔍 Parmak izi (SHA-256):")
    print(f"      {fingerprint}")
    print()
    print("⚠️  DİKKAT: server_private.pem dosyasını kimseyle paylaşmayın!")
    print("   Bu dosya .gitignore ile versiyon kontrolünden hariç tutulmuştur.")


if __name__ == "__main__":
    main()
