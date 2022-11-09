from micropython import const
from typing import TYPE_CHECKING

from trezor.crypto.hashlib import blake2b
from trezor.utils import HashWriter
from trezor.wire import DataError

from ..writers import TX_HASH_SIZE, write_bytes_reversed, write_uint32, write_uint64
from .bitcoinlike import Bitcoinlike

if TYPE_CHECKING:
    from trezor.messages import PrevTx, SignTx, TxInput, TxOutput
    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain
    from . import approvers
    from typing import Sequence
    from .sig_hasher import SigHasher
    from .tx_info import OriginalTxInfo, TxInfo
    from ..common import SigHashType
    from ..writers import Writer

_OVERWINTERED = const(0x8000_0000)


class Zip243SigHasher:
    def __init__(self) -> None:
        self.h_prevouts = HashWriter(blake2b(outlen=32, personal=b"ZcashPrevoutHash"))
        self.h_sequence = HashWriter(blake2b(outlen=32, personal=b"ZcashSequencHash"))
        self.h_outputs = HashWriter(blake2b(outlen=32, personal=b"ZcashOutputsHash"))

    def add_input(self, txi: TxInput, script_pubkey: bytes) -> None:
        write_bytes_reversed(self.h_prevouts, txi.prev_hash, TX_HASH_SIZE)
        write_uint32(self.h_prevouts, txi.prev_index)
        write_uint32(self.h_sequence, txi.sequence)

    def add_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        from ..writers import write_tx_output

        write_tx_output(self.h_outputs, txo, script_pubkey)

    def hash143(
        self,
        txi: TxInput,
        public_keys: Sequence[bytes | memoryview],
        threshold: int,
        tx: SignTx | PrevTx,
        coin: CoinInfo,
        hash_type: int,
    ) -> bytes:
        import ustruct as struct
        from ..scripts import write_bip143_script_code_prefixed
        from ..writers import get_tx_hash, write_bytes_fixed

        h_preimage = HashWriter(
            blake2b(
                outlen=32,
                personal=b"ZcashSigHash" + struct.pack("<I", tx.branch_id),
            )
        )

        assert tx.version_group_id is not None
        assert tx.expiry is not None
        zero_hash = b"\x00" * TX_HASH_SIZE

        # 1. nVersion | fOverwintered
        write_uint32(h_preimage, tx.version | _OVERWINTERED)
        # 2. nVersionGroupId
        write_uint32(h_preimage, tx.version_group_id)
        # 3. hashPrevouts
        write_bytes_fixed(h_preimage, get_tx_hash(self.h_prevouts), TX_HASH_SIZE)
        # 4. hashSequence
        write_bytes_fixed(h_preimage, get_tx_hash(self.h_sequence), TX_HASH_SIZE)
        # 5. hashOutputs
        write_bytes_fixed(h_preimage, get_tx_hash(self.h_outputs), TX_HASH_SIZE)
        # 6. hashJoinSplits
        write_bytes_fixed(h_preimage, zero_hash, TX_HASH_SIZE)
        # 7. hashShieldedSpends
        write_bytes_fixed(h_preimage, zero_hash, TX_HASH_SIZE)
        # 8. hashShieldedOutputs
        write_bytes_fixed(h_preimage, zero_hash, TX_HASH_SIZE)
        # 9. nLockTime
        write_uint32(h_preimage, tx.lock_time)
        # 10. expiryHeight
        write_uint32(h_preimage, tx.expiry)
        # 11. valueBalance
        write_uint64(h_preimage, 0)
        # 12. nHashType
        write_uint32(h_preimage, hash_type)
        # 13a. outpoint
        write_bytes_reversed(h_preimage, txi.prev_hash, TX_HASH_SIZE)
        write_uint32(h_preimage, txi.prev_index)
        # 13b. scriptCode
        write_bip143_script_code_prefixed(h_preimage, txi, public_keys, threshold, coin)
        # 13c. value
        write_uint64(h_preimage, txi.amount)
        # 13d. nSequence
        write_uint32(h_preimage, txi.sequence)

        return get_tx_hash(h_preimage)

    def hash341(
        self,
        i: int,
        tx: SignTx | PrevTx,
        sighash_type: SigHashType,
    ) -> bytes:
        raise NotImplementedError

    def hash_zip244(
        self,
        txi: TxInput | None,
        script_pubkey: bytes | None,
    ) -> bytes:
        raise NotImplementedError


class ZcashV4(Bitcoinlike):
    def __init__(
        self,
        tx: SignTx,
        keychain: Keychain,
        coin: CoinInfo,
        approver: approvers.Approver | None,
    ) -> None:
        from trezor.utils import ensure

        ensure(coin.overwintered)
        super().__init__(tx, keychain, coin, approver)

        if tx.version != 4:
            raise DataError("Unsupported transaction version.")

    def create_sig_hasher(self, tx: SignTx | PrevTx) -> SigHasher:
        return Zip243SigHasher()

    async def step7_finish(self) -> None:
        from apps.common.writers import write_compact_size
        from . import helpers

        serialized_tx = self.serialized_tx  # local_cache_attribute

        if self.serialize:
            self.write_tx_footer(serialized_tx, self.tx_info.tx)

            write_uint64(serialized_tx, 0)  # valueBalance
            write_compact_size(serialized_tx, 0)  # nShieldedSpend
            write_compact_size(serialized_tx, 0)  # nShieldedOutput
            write_compact_size(serialized_tx, 0)  # nJoinSplit

        await helpers.request_tx_finish(self.tx_req)

    async def sign_nonsegwit_input(self, i_sign: int) -> None:
        await self.sign_nonsegwit_bip143_input(i_sign)

    async def get_tx_digest(
        self,
        i: int,
        txi: TxInput,
        tx_info: TxInfo | OriginalTxInfo,
        public_keys: Sequence[bytes | memoryview],
        threshold: int,
        script_pubkey: bytes,
        tx_hash: bytes | None = None,
    ) -> bytes:
        return tx_info.sig_hasher.hash143(
            txi,
            public_keys,
            threshold,
            tx_info.tx,
            self.coin,
            self.get_sighash_type(txi),
        )

    def write_tx_header(
        self, w: Writer, tx: SignTx | PrevTx, witness_marker: bool
    ) -> None:
        if tx.version < 3:
            # pre-overwinter
            write_uint32(w, tx.version)
        else:
            if tx.version_group_id is None:
                raise DataError("Version group ID is missing")
            # nVersion | fOverwintered
            write_uint32(w, tx.version | _OVERWINTERED)
            write_uint32(w, tx.version_group_id)  # nVersionGroupId

    def write_tx_footer(self, w: Writer, tx: SignTx | PrevTx) -> None:
        assert tx.expiry is not None  # checked in sanitize_*
        write_uint32(w, tx.lock_time)
        if tx.version >= 3:
            write_uint32(w, tx.expiry)  # expiryHeight
