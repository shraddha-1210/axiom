import hashlib
import json
import os
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import (
    Encoding, PrivateFormat, NoEncryption
)

# Directory where the persistent key is stored.
# In production, swap this for Google Secret Manager / Cloud KMS.
_KEY_DIR = os.path.join(os.path.dirname(__file__), "keys")
_KEY_PATH = os.path.join(_KEY_DIR, "local_hsm.pem")


def _load_or_generate_key() -> rsa.RSAPrivateKey:
    """
    Loads the RSA private key from disk, or generates + persists a new one.

    This prevents the ephemeral-key bug where a new keypair is created on
    every process restart, making all previously signed manifests
    unverifiable.
    """
    if os.path.exists(_KEY_PATH):
        with open(_KEY_PATH, "rb") as f:
            key = serialization.load_pem_private_key(f.read(), password=None)
        print("✓ Loaded persisted HSM key from disk")
        return key

    # First run: generate and persist
    os.makedirs(_KEY_DIR, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with open(_KEY_PATH, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=Encoding.PEM,
                format=PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=NoEncryption()
            )
        )
    print("✓ Generated new HSM key and persisted to disk")
    return key


class LocalC2PA:
    def __init__(self):
        # Load persisted key instead of generating a new ephemeral one.
        self.private_key = _load_or_generate_key()
        self.public_key = self.private_key.public_key()

    def generate_file_hash(self, filepath: str) -> str:
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def create_and_sign_manifest(self, filepath: str, asset_id: str, uploader_id: str):
        file_hash = self.generate_file_hash(filepath)

        manifest = {
            "claim_generator": "SentinelMedia Local HSM MVP",
            "claim_generator_info": [
                {"name": "SentinelMedia Provenance Node", "version": "2.0"}
            ],
            "title": f"Asset {asset_id}",
            "instance_id": f"xmp:iid:{asset_id}",
            "ingredients": [],
            "assertions": [
                {
                    "label": "c2pa.actions",
                    "data": {
                        "actions": [
                            {"action": "c2pa.created"}
                        ]
                    }
                },
                {
                    "label": "c2pa.hash.data",
                    "data": {
                        "exclusions": [],
                        "alg": "sha256",
                        "hash": file_hash
                    }
                },
                {
                    "label": "stml.provenance.metadata",
                    "data": {
                        "uploader": uploader_id,
                        # Fixed: use timezone-aware UTC timestamp (utcnow() is deprecated in 3.12+)
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }
            ],
            "signature_info": {
                "algorithm": "RSASSA-PSS",
                "hashing": "SHA-256",
                "issuer": "SentinelMedia Local Root"
            }
        }

        manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")

        signature = self.private_key.sign(
            manifest_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        return manifest, signature.hex()


c2pa_engine = LocalC2PA()
