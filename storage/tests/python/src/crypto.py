from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from . import consts, prng


def derive_kek_keiv(salt: bytes, pin: str) -> (bytes, bytes):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=consts.KEK_SIZE + consts.KEIV_SIZE,
        salt=bytes(salt),
        iterations=10000,
        backend=default_backend(),
    )
    pbkdf_output = kdf.derive(pin.encode())
    # the first 256b is Key Encryption Key
    kek = pbkdf_output[: consts.KEK_SIZE]
    # following with 96b of Initialization Vector
    keiv = pbkdf_output[consts.KEK_SIZE :]

    return kek, keiv


def chacha_poly_encrypt(
    key: bytes, iv: bytes, data: bytes, additional_data: bytes = None
) -> (bytes, bytes):
    chacha = ChaCha20Poly1305(key)
    chacha_output = chacha.encrypt(iv, bytes(data), additional_data)
    # cipher text and 128b authentication tag
    return chacha_output[: len(data)], chacha_output[len(data) :]


def chacha_poly_decrypt(
    key: bytes, app_key: int, iv: bytes, data: bytes, additional_data: bytes = None
) -> bytes:
    chacha = ChaCha20Poly1305(key)
    chacha_output = chacha.decrypt(bytes(iv), bytes(data), additional_data)
    return chacha_output


def decrypt_edek_esak(
    pin: str, salt: bytes, edek_esak: bytes, pvc: bytes
) -> (bytes, bytes):
    """
    Decrypts EDEK, ESAK to DEK, SAK and checks PIN in the process.
    Raises:
        InvalidPinError: if PIN is invalid
    """
    kek, keiv = derive_kek_keiv(salt, pin)

    algorithm = algorithms.ChaCha20(kek, (1).to_bytes(4, "little") + keiv)
    cipher = Cipher(algorithm, mode=None, backend=default_backend())
    decryptor = cipher.decryptor()
    dek_sak = decryptor.update(bytes(edek_esak))
    dek = dek_sak[: consts.DEK_SIZE]
    sak = dek_sak[consts.DEK_SIZE :]

    if not validate_pin(kek, keiv, dek_sak, pvc):
        raise InvalidPinError("Invalid PIN")

    return dek, sak


def validate_pin(kek: bytes, keiv: bytes, dek_sak: bytes, pvc: bytes) -> bool:
    """
    This a little bit hackish. We do not store the whole
    authentication tag so we can't decrypt using ChaCha20Poly1305
    because it obviously checks the tag first and fails.
    So we are using the sole ChaCha20 cipher to decipher and then encrypt
    again with Chacha20Poly1305 here to get the tag and compare it to PVC.
    """
    _, tag = chacha_poly_encrypt(kek, keiv, dek_sak)
    prng.random32()
    prng.random32()
    return tag[: consts.PVC_SIZE] == pvc


def calculate_hmacs(sak: bytes, keys: bytes) -> bytes:
    """
    This calculates HMAC-SHA-256(SAK, (XOR_i) HMAC-SHA-256(SAK, KEY_i)).
    In other words, it does HMAC for every KEY and XORs it all together.
    One more final HMAC is then performed on the result.
    """
    hmacs = _hmac(sak, keys[0])
    for key in keys[1:]:
        hmacs = _xor(hmacs, _hmac(sak, key))
    return _final_hmac(sak, hmacs)


def init_hmacs(sak: bytes) -> bytes:
    return _final_hmac(sak, b"\x00" * hashes.SHA256.digest_size)


def _final_hmac(sak: bytes, data: bytes) -> bytes:
    return _hmac(sak, data)[: consts.SAT_SIZE]


def _hmac(key: bytes, data: bytes) -> bytes:
    h = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())
    h.update(data)
    return h.finalize()


def _xor(first: bytes, second: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(first, second))


class InvalidPinError(ValueError):
    pass
