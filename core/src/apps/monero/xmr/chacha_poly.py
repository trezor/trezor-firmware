from typing import TYPE_CHECKING

from trezor.crypto import chacha20poly1305 as ChaCha20Poly1305

if TYPE_CHECKING:
    from buffer_types import AnyBytes


def encrypt(
    key: AnyBytes, plaintext: AnyBytes, associated_data: AnyBytes | None = None
) -> tuple[bytes, bytes]:
    """
    Uses ChaCha20Poly1305 for encryption
    """
    from trezor.crypto import random

    nonce = random.bytes(12)
    cipher = ChaCha20Poly1305(key, nonce)
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

    cipher = ChaCha20Poly1305(key, iv)
    if associated_data:
        cipher.auth(associated_data)
    exp_tag, ciphertext = ciphertext[-16:], ciphertext[:-16]
    plaintext = cipher.decrypt(ciphertext)
    try:
        cipher.finish(exp_tag)
    except RuntimeError:
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
