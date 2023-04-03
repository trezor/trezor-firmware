from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.utils import HashContext

    from .serialize_messages.tx_rsig_bulletproof import BulletproofPlus


class PreMlsagHasher:
    """
    Iterative construction of the pre_mlsag_hash
    """

    def __init__(self) -> None:
        from apps.monero.xmr import crypto_helpers
        from apps.monero.xmr.keccak_hasher import KeccakXmrArchive

        self.state = 0
        self.kc_master: HashContext = crypto_helpers.get_keccak()
        self.rsig_hasher: HashContext = crypto_helpers.get_keccak()
        self.rtcsig_hasher: KeccakXmrArchive = KeccakXmrArchive()

    def init(self) -> None:
        if self.state != 0:
            raise ValueError("State error")

        self.state = 1

    def set_message(self, message: bytes) -> None:
        self.kc_master.update(message)

    def set_type_fee(self, rv_type: int, fee: int) -> None:
        if self.state != 1:
            raise ValueError("State error")
        self.state = 2
        self.rtcsig_hasher.uint(rv_type, 1)  # UInt8
        self.rtcsig_hasher.uvarint(fee)  # UVarintType

    def set_ecdh(self, ecdh: bytes) -> None:
        if self.state not in (2, 3, 4):
            raise ValueError("State error")
        self.state = 4
        self.rtcsig_hasher.buffer(ecdh)

    def set_out_pk_commitment(self, out_pk_commitment: bytes) -> None:
        if self.state not in (4, 5):
            raise ValueError("State error")
        self.state = 5
        self.rtcsig_hasher.buffer(out_pk_commitment)  # ECKey

    def rctsig_base_done(self) -> None:
        if self.state != 5:
            raise ValueError("State error")
        self.state = 6

        c_hash = self.rtcsig_hasher.get_digest()
        self.kc_master.update(c_hash)
        self.rtcsig_hasher = None  # type: ignore

    def rsig_val(
        self, p: bytes | list[bytes] | BulletproofPlus, raw: bool = False
    ) -> None:
        if self.state == 8:
            raise ValueError("State error")
        update = self.rsig_hasher.update  # local_cache_attribute

        if raw:
            # Avoiding problem with the memory fragmentation.
            # If the range proof is passed as a list, hash each element
            # as the range proof is split to multiple byte arrays while
            # preserving the byte ordering
            if isinstance(p, list):
                for x in p:
                    update(x)
            else:
                assert isinstance(p, bytes)
                update(p)
            return

        # Hash Bulletproof
        fields = (p.A, p.A1, p.B, p.r1, p.s1, p.d1)
        for fld in fields:
            update(fld)

        del (fields,)
        for i in range(len(p.L)):
            update(p.L[i])
        for i in range(len(p.R)):
            update(p.R[i])

    def get_digest(self) -> bytes:
        if self.state != 6:
            raise ValueError("State error")
        self.state = 8

        c_hash = self.rsig_hasher.digest()
        self.rsig_hasher = None  # type: ignore

        self.kc_master.update(c_hash)
        return self.kc_master.digest()
