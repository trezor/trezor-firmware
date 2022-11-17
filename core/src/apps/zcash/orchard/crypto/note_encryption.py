import gc
from micropython import const
from typing import TYPE_CHECKING

from trezor.crypto import chacha20poly1305
from trezor.crypto.hashlib import blake2b
from trezor.crypto.pallas import Point
from trezor.utils import empty_bytearray, ensure

from apps.common.writers import write_bytes_fixed

from .note import Note

if TYPE_CHECKING:
    from typing import Iterable
    from ..random import ActionShieldingRng

BLOCK_SIZE = const(64)
ENC_CIPHERTEXT_SIZE = const(580)
OUT_CIPHERTEXT_SIZE = const(80)


# https://zips.z.cash/protocol/nu5.pdf#concreteorchardkdf
def kdf_orchard(shared_secret: Point, ephemeral_key: bytes) -> bytes:
    digest = blake2b(outlen=32, personal=b"Zcash_OrchardKDF")
    digest.update(shared_secret.to_bytes())
    digest.update(ephemeral_key)
    return digest.digest()


# https://zips.z.cash/protocol/nu5.pdf#concreteprfs
def prf_ock_orchard(
    ovk: bytes,
    cv: bytes,
    cmx: bytes,
    ephemeral_key: bytes,
) -> bytes:
    digest = blake2b(outlen=32, personal=b"Zcash_Orchardock")
    digest.update(ovk)
    digest.update(cv)
    digest.update(cmx)
    digest.update(ephemeral_key)
    return digest.digest()


def chunks(size: int, length: int) -> Iterable[tuple[int, int]]:
    offset = 0
    while offset + size <= length:
        yield offset, offset + size
        offset += size
    if offset < length:
        yield offset, length
    return


# https://zips.z.cash/protocol/nu5.pdf#concretesym
def sym_encrypt(key: bytes, buffer: bytearray) -> None:
    nonce = 12 * b"\x00"
    cipher = chacha20poly1305(key, nonce)
    for i, j in chunks(BLOCK_SIZE, len(buffer)):
        buffer[i:j] = cipher.encrypt(buffer[i:j])
    buffer.extend(cipher.finish())  # append tag


class TransmittedNoteCiphertext:
    def __init__(
        self,
        epk_bytes: bytes,
        enc_ciphertext: bytes,
        out_ciphertext: bytes,
    ):
        self.epk_bytes = epk_bytes
        self.enc_ciphertext = enc_ciphertext
        self.out_ciphertext = out_ciphertext


# https://zips.z.cash/protocol/nu5.pdf#saplingandorchardencrypt
def encrypt_note(
    note: Note,
    memo: str | bytes | None,
    cv_new: Point,
    cm_new: Point,
    ovk: bytes | None,
    rng: ActionShieldingRng,
) -> TransmittedNoteCiphertext:
    np = empty_bytearray(ENC_CIPHERTEXT_SIZE)
    note.write_plaintext(np, memo)

    esk = note.esk()
    ensure(esk)  # esk != 0
    g_d = note.recipient.g_d()
    pk_d = note.recipient.pk_d

    # https://zips.z.cash/protocol/nu5.pdf#concreteorchardkeyagreement
    epk = esk * g_d  # KA.DerivePublic
    shared_secret = esk * pk_d  # KA.Agree

    ephemeral_key = epk.to_bytes()
    k_enc = kdf_orchard(shared_secret, ephemeral_key)
    sym_encrypt(k_enc, np)

    op = empty_bytearray(OUT_CIPHERTEXT_SIZE)
    if ovk is None:
        ock = rng.ock()
        write_bytes_fixed(op, rng.op(), 64)
    else:
        cv = cv_new.to_bytes()
        cmx = cm_new.extract().to_bytes()
        ock = prf_ock_orchard(ovk, cv, cmx, ephemeral_key)
        write_bytes_fixed(op, pk_d.to_bytes(), 32)
        write_bytes_fixed(op, esk.to_bytes(), 32)

    sym_encrypt(ock, op)

    gc.collect()
    return TransmittedNoteCiphertext(
        epk_bytes=ephemeral_key,
        enc_ciphertext=bytes(np),
        out_ciphertext=bytes(op),
    )
