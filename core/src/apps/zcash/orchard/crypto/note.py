from typing import TYPE_CHECKING

from trezor.crypto.hashlib import poseidon
from trezor.crypto.pallas import Fp, Point, Scalar, to_base, to_scalar
from trezor.messages import ZcashOrchardInput

from apps.common.writers import (
    write_bytes_fixed,
    write_bytes_unchecked,
    write_uint8,
    write_uint64_le,
)

from .address import Address
from .generators import NOTE_COMMITMENT_BASE, NOTE_COMMITMENT_Q, NULLIFIER_K_BASE
from .sinsemilla import Sinsemilla
from .utils import i2lebsp, leos2bsp, prf_expand

if TYPE_CHECKING:
    from trezor.utils import Writer


class Note:
    def __init__(self, recipient: Address, value: int, rho: Fp, rseed: bytes) -> None:
        self.recipient = recipient
        self.value = value
        self.rho = rho
        self.rseed = rseed

    @staticmethod
    def from_message(msg: ZcashOrchardInput) -> "Note":
        return Note(
            Address.from_bytes(msg.recipient),
            msg.value,
            Fp(msg.rho),
            msg.rseed,
        )

    # `esk`, `rcm` and `psi` derivation defined in
    # https://zips.z.cash/protocol/protocol.pdf#orchardsend
    def _expand(self, domain: bytes) -> bytes:
        return prf_expand(self.rseed, domain + self.rho.to_bytes())

    def esk(self) -> Scalar:
        return to_scalar(self._expand(b"\x04"))

    def rcm(self) -> Scalar:
        return to_scalar(self._expand(b"\x05"))

    def psi(self) -> Fp:
        return to_base(self._expand(b"\x09"))

    # https://zips.z.cash/protocol/nu5.pdf#concreteNotecommit
    def commitment(self) -> Point:
        h = Sinsemilla(NOTE_COMMITMENT_Q)
        h.update(leos2bsp(self.recipient.g_d().to_bytes()))
        h.update(leos2bsp(self.recipient.pk_d.to_bytes()))
        h.update(i2lebsp(64, self.value))
        h.update(i2lebsp(255, self.rho))
        h.update(i2lebsp(255, self.psi()))
        return h.finalize() + self.rcm() * NOTE_COMMITMENT_BASE

    # https://zips.z.cash/protocol/protocol.pdf#commitmentsandnullifiers
    def nullifier(self, nk: Fp) -> Fp:
        base = poseidon(nk, self.rho) + self.psi()
        scalar = Scalar(base.to_bytes())
        point = scalar * NULLIFIER_K_BASE + self.commitment()
        return point.extract()

    # https://zips.z.cash/protocol/nu5.pdf#notept
    def write_plaintext(self, w: Writer, memo: str | bytes | None) -> None:
        write_uint8(w, 0x02)
        write_bytes_fixed(w, self.recipient.d, 11)
        write_uint64_le(w, self.value)
        write_bytes_fixed(w, self.rseed, 32)
        write_memo(w, memo)


# https://zips.z.cash/zip-0302
def write_memo(w: Writer, memo: str | bytes | None) -> None:
    """Encodes a memo according to the ZIP-302 Standardized Memo Field Format"""
    if memo is None:
        write_uint8(w, 0xF6)
        padding_length = 511
    elif isinstance(memo, str):
        encoded = memo.encode()
        if len(encoded) > 512:
            raise ValueError("Memo is too long.")
        write_bytes_unchecked(w, encoded)
        padding_length = 512 - len(encoded)
    else:
        assert 0xF7 <= memo[0] <= 0xFF
        write_bytes_fixed(w, memo, 512)
        padding_length = 0

    write_bytes_unchecked(w, padding_length * b"\x00")
