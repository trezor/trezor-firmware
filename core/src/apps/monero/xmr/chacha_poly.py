from typing import TYPE_CHECKING

from trezor.crypto import (
    AuthenticationError,
    chacha20poly1305_decrypt,
    chacha20poly1305_encrypt,
)

if TYPE_CHECKING:
    from buffer_types import AnyBytes


def encrypt(
    key: AnyBytes, plaintext: AnyBytes, associated_data: AnyBytes | None = None
) -> tuple[bytes, bytes]:
    """
    Uses ChaCha20Poly1305 for encryption
    """
    from trezor.crypto import random

    nonce = random.bytes(chacha20poly1305_encrypt.nonce_size)
    cipher = chacha20poly1305_encrypt(key, nonce)
    if associated_data:
        cipher.auth(associated_data)
    ciphertext = cipher.encrypt(plaintext)
    tag = cipher.finish()
    return nonce, ciphertext + tag


def _decrypt(
    key: AnyBytes,
    iv: AnyBytes,
    ciphertext: AnyBytes,
    associated_data: AnyBytes | None = None,
) -> bytes:
    """
    ChaCha20Poly1305 decryption
    """

    cipher = chacha20poly1305_decrypt(key, iv)
    if associated_data:
        cipher.auth(associated_data)
    tag_size = chacha20poly1305_decrypt.tag_size
    exp_tag, ciphertext = ciphertext[-tag_size:], ciphertext[:-tag_size]
    plaintext = cipher.decrypt(ciphertext)
    try:
        cipher.finish(exp_tag)
    except AuthenticationError:
        raise ValueError("tag invalid")

    return plaintext


def encrypt_pack(
    key: AnyBytes, plaintext: AnyBytes, associated_data: AnyBytes | None = None
) -> bytes:
    b = encrypt(key, plaintext, associated_data)
    return b[0] + b[1]


def decrypt_pack(key: AnyBytes, ciphertext: AnyBytes) -> bytes:
    cp = memoryview(ciphertext)
    return _decrypt(
        key=key,
        iv=cp[:12],
        ciphertext=cp[12:],
    )
