import hmac
import random
from hashlib import sha256
from typing import NewType

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


def hmac_hash(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, sha256).digest()


PrivateKey = NewType("PrivateKey", bytes)  # 32 bytes
PublicKey = NewType("PublicKey", bytes)  # 32 bytes

AEAD_NONCE_SIZE_BYTES = 12
AEAD_TAG_SIZE_BYTES = 16


class DecryptionError(BaseException):
    pass


def aead_encrypt(
    key: bytes, nonce: bytes, plaintext: bytes, associated_data: bytes = b""
) -> bytes:
    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, associated_data)
    return ciphertext_with_tag


def aead_decrypt(
    key: bytes, nonce: bytes, ciphertext_with_tag: bytes, associated_data: bytes = b""
) -> bytes:
    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, associated_data)
        return plaintext
    except Exception:
        raise DecryptionError()


def generate_private_key() -> PrivateKey:
    return PrivateKey(X25519PrivateKey.generate().private_bytes_raw())


def derive_public_key(private_key: PrivateKey) -> PublicKey:
    return PublicKey(
        X25519PrivateKey.from_private_bytes(private_key)
        .public_key()
        .public_bytes(Encoding.Raw, PublicFormat.Raw)
    )


def hash(data: bytes) -> bytes:
    return sha256(data).digest()


def random_bytes(length: int) -> bytes:
    return random.randbytes(length)


def generate_keypair() -> tuple[PrivateKey, PublicKey]:
    private_key = X25519PrivateKey.generate()
    return PrivateKey(private_key.private_bytes_raw()), PublicKey(
        private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    )


def dh(private_key_bytes: bytes, public_key_bytes: bytes) -> bytes:
    return X25519PrivateKey.from_private_bytes(private_key_bytes).exchange(
        X25519PublicKey.from_public_bytes(public_key_bytes)
    )


def public_key(private_key_bytes: PrivateKey) -> PublicKey:
    return PublicKey(
        X25519PrivateKey.from_private_bytes(private_key_bytes)
        .public_key()
        .public_bytes(Encoding.Raw, PublicFormat.Raw)
    )
