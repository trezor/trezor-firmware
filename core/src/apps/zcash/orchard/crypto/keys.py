# https://zips.z.cash/protocol/protocol.pdf#orchardkeycomponents

from trezor.crypto.pallas import Fp, Scalar, to_base, to_scalar
from trezor.utils import ensure

from . import ff1
from .address import Address
from .generators import IVK_COMMITMENT_BASE, IVK_COMMITMENT_Q, SPENDING_KEY_BASE
from .sinsemilla import Sinsemilla
from .utils import i2lebsp, prf_expand


def sk_to_ask(sk: bytes) -> Scalar:
    """Derives Spend Authorizing Key from Spending Key."""
    ask = to_scalar(prf_expand(sk, b"\x06"))
    akP = ask * SPENDING_KEY_BASE
    if akP.to_bytes()[-1] & 0x80 != 0:
        ask = -ask
    ensure(ask)  # ask != 0
    return ask


class FullViewingKey:
    def __init__(self, ak: Fp, nk: Fp, rivk: Scalar):
        self.ak = ak
        self.nk = nk
        self.rivk = rivk

        self._ivk: Scalar | None = None
        self._ovk: bytes | None = None
        self._dk: bytes | None = None

    @property
    def ivk(self) -> Scalar:
        if self._ivk is None:
            self._derive_ivk()
        assert self._ivk is not None
        return self._ivk

    @property
    def dk(self) -> bytes:
        if self._dk is None:
            self._derive_dk_and_ovk()
        assert self._dk is not None  # typing
        return self._dk

    @property
    def ovk(self) -> bytes:
        if self._ovk is None:
            self._derive_dk_and_ovk()
        assert self._ovk is not None  # typing
        return self._ovk

    @staticmethod
    def from_spending_key(sk: bytes) -> "FullViewingKey":
        ask = to_scalar(prf_expand(sk, b"\x06"))
        nk = to_base(prf_expand(sk, b"\x07"))
        rivk = to_scalar(prf_expand(sk, b"\x08"))
        ensure(ask)  # ask != 0
        ak = (ask * SPENDING_KEY_BASE).extract()
        return FullViewingKey(ak, nk, rivk)

    # https://zips.z.cash/protocol/protocol.pdf#orchardfullviewingkeyencoding
    def to_bytes(self) -> bytes:
        return self.ak.to_bytes() + self.nk.to_bytes() + self.rivk.to_bytes()

    # https://zips.z.cash/protocol/protocol.pdf#orchardinviewingkeyencoding
    def incoming_viewing_key(self) -> bytes:
        if self.ivk is None:
            self._derive_ivk()
        if self.dk is None:
            self._derive_dk_and_ovk()
        return self.dk + self.ivk.to_bytes()

    def outgoing_viewing_key(self) -> bytes:
        if self.ovk is None:
            self._derive_dk_and_ovk()
        return self.ovk

    def _derive_ivk(self) -> None:
        ivk_base = commit_ivk(self.rivk, self.ak, self.nk)
        assert ivk_base is not None
        # Now convert Fp to Scalar.
        # This requires no modular reduction because
        # Pallas' base field is smaller than its scalar field.
        self._ivk = Scalar(ivk_base.to_bytes())
        ensure(self._ivk)  # ivk != 0

    def _derive_dk_and_ovk(self) -> None:
        K = self.rivk.to_bytes()
        R = prf_expand(K, b"\x82" + self.ak.to_bytes() + self.nk.to_bytes())
        self._dk = R[:32]
        self._ovk = R[32:]

    def address(self, index: int = 0) -> Address:
        """Derives a diversified shielded address."""
        d = ff1.encrypt_diversifier_index(self.dk, index)
        return Address.from_ivk(d, self.ivk)

    def internal(self) -> "FullViewingKey":
        K = self.rivk.to_bytes()
        rivk_internal = to_scalar(
            prf_expand(K, b"\x83" + self.ak.to_bytes() + self.nk.to_bytes())
        )
        return FullViewingKey(self.ak, self.nk, rivk_internal)


# https://zips.z.cash/protocol/nu5.pdf#concreteNotecommit
def commit_ivk(rivk: Scalar, ak: Fp, nk: Fp) -> Fp:
    h = Sinsemilla(IVK_COMMITMENT_Q)
    h.update(i2lebsp(255, ak))
    h.update(i2lebsp(255, nk))
    commitment = h.finalize() + rivk * IVK_COMMITMENT_BASE
    return commitment.extract()
