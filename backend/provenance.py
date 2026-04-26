import hashlib
import json
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

class LocalC2PA:
    def __init__(self):
        # Generate an ephemeral keypair to mimic an HSM for the $0 MVP
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        self.public_key = self.private_key.public_key()

    def generate_file_hash(self, filepath: str) -> str:
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def create_and_sign_manifest(self, filepath: str, asset_id: str, uploader_id: str):
        file_hash = self.generate_file_hash(filepath)
        
        manifest = {
            "asset_id": asset_id,
            "uploader": uploader_id,
            "timestamp": datetime.utcnow().isoformat(),
            "file_sha256": file_hash,
            "algorithm": "Local-RSA-2048-MVP"
        }
        
        manifest_bytes = json.dumps(manifest, sort_keys=True).encode('utf-8')
        
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
