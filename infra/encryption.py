from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import struct
import json

MAGIC = b'LVLT'
VERSION = 1


def encrypt_data(data: dict, password: str) -> bytes:
    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
    key = _derive_key(password)
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, json_bytes, None)
    return MAGIC + struct.pack('<I', VERSION) + nonce + ciphertext


def decrypt_data(raw: bytes, password: str) -> dict:
    if raw[:4] != MAGIC:
        raise ValueError('无效的 .linkvault 文件格式')
    version = struct.unpack('<I', raw[4:8])[0]
    nonce = raw[8:20]
    ciphertext = raw[20:]
    key = _derive_key(password)
    aesgcm = AESGCM(key)
    json_bytes = aesgcm.decrypt(nonce, ciphertext, None)
    return json.loads(json_bytes.decode('utf-8'))


def _derive_key(password: str) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    salt = b'LinkVaultSalt2026'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return kdf.derive(password.encode('utf-8'))