from trezor.crypto import chacha20poly1305 as ChaCha20Poly1305


def encrypt(key: bytes, plaintext: bytes, associated_data: bytes | None = None):
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
    return nonce, ciphertext + tag, b""


def _decrypt(
    key: bytes,
    iv: bytes,
    ciphertext: bytes,
    associated_data: bytes | None = None,
):
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


def encrypt_pack(key: bytes, plaintext: bytes, associated_data: bytes | None = None):
    b = encrypt(key, plaintext, associated_data)
    return b[0] + b[1]


def decrypt_pack(key: bytes, ciphertext: bytes):
    cp = memoryview(ciphertext)
    return _decrypt(
        key=key,
        iv=cp[:12],
        ciphertext=cp[12:],
    )
