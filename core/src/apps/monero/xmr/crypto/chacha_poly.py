from trezor.crypto import chacha20poly1305 as ChaCha20Poly1305, monero, random


def encrypt(key: bytes, plaintext: bytes, associated_data: bytes | None = None):
    """
    Uses ChaCha20Poly1305 for encryption
    """
    nonce = random.bytes(12)
    cipher = ChaCha20Poly1305(key, nonce)
    if associated_data:
        cipher.auth(associated_data)
    ciphertext = cipher.encrypt(plaintext)
    tag = cipher.finish()
    return nonce, ciphertext + tag, b""


def decrypt(
    key: bytes,
    iv: bytes,
    ciphertext: bytes,
    tag: bytes | None = None,
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
    tag = cipher.finish()
    if not monero.ct_equals(tag, exp_tag):
        raise ValueError("tag invalid")

    return plaintext


def encrypt_pack(key: bytes, plaintext: bytes, associated_data: bytes | None = None):
    b = encrypt(key, plaintext, associated_data)
    return b[0] + b[1]


def decrypt_pack(key: bytes, ciphertext: bytes):
    cp = memoryview(ciphertext)
    return decrypt(key, cp[:12], cp[12:], None)
