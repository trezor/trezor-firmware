from apps.monero.xmr import crypto
from apps.monero.xmr.keccak_hasher import KeccakXmrArchive

if False:
    from typing import List, Union
    from apps.monero.xmr.serialize_messages.tx_rsig_bulletproof import Bulletproof


class PreMlsagHasher:
    """
    Iterative construction of the pre_mlsag_hash
    """

    def __init__(self):
        self.state = 0
        self.kc_master = crypto.get_keccak()
        self.rsig_hasher = crypto.get_keccak()
        self.rtcsig_hasher = KeccakXmrArchive()

    def init(self):
        if self.state != 0:
            raise ValueError("State error")

        self.state = 1

    def set_message(self, message: bytes):
        self.kc_master.update(message)

    def set_type_fee(self, rv_type: int, fee: int):
        if self.state != 1:
            raise ValueError("State error")
        self.state = 2
        self.rtcsig_hasher.uint(rv_type, 1)  # UInt8
        self.rtcsig_hasher.uvarint(fee)  # UVarintType

    def set_ecdh(self, ecdh: bytes):
        if self.state != 2 and self.state != 3 and self.state != 4:
            raise ValueError("State error")
        self.state = 4
        self.rtcsig_hasher.buffer(ecdh)

    def set_out_pk_commitment(self, out_pk_commitment: bytes):
        if self.state != 4 and self.state != 5:
            raise ValueError("State error")
        self.state = 5
        self.rtcsig_hasher.buffer(out_pk_commitment)  # ECKey

    def rctsig_base_done(self):
        if self.state != 5:
            raise ValueError("State error")
        self.state = 6

        c_hash = self.rtcsig_hasher.get_digest()
        self.kc_master.update(c_hash)
        self.rtcsig_hasher = None

    def rsig_val(self, p: Union[bytes, List[bytes], Bulletproof], raw: bool = False):
        if self.state == 8:
            raise ValueError("State error")

        if raw:
            # Avoiding problem with the memory fragmentation.
            # If the range proof is passed as a list, hash each element
            # as the range proof is split to multiple byte arrays while
            # preserving the byte ordering
            if isinstance(p, list):
                for x in p:
                    self.rsig_hasher.update(x)
            else:
                self.rsig_hasher.update(p)
            return

        # Hash Bulletproof
        self.rsig_hasher.update(p.A)
        self.rsig_hasher.update(p.S)
        self.rsig_hasher.update(p.T1)
        self.rsig_hasher.update(p.T2)
        self.rsig_hasher.update(p.taux)
        self.rsig_hasher.update(p.mu)
        for i in range(len(p.L)):
            self.rsig_hasher.update(p.L[i])
        for i in range(len(p.R)):
            self.rsig_hasher.update(p.R[i])
        self.rsig_hasher.update(p.a)
        self.rsig_hasher.update(p.b)
        self.rsig_hasher.update(p.t)

    def get_digest(self) -> bytes:
        if self.state != 6:
            raise ValueError("State error")
        self.state = 8

        c_hash = self.rsig_hasher.digest()
        self.rsig_hasher = None

        self.kc_master.update(c_hash)
        return self.kc_master.digest()
