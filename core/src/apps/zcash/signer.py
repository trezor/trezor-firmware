from micropython import const

from .orchard.signer import OrchardSigner
from . import sig_hasher
from .layout import UiConfirmOrchardOutput

from trezor import log
from trezor.utils import ensure
from trezor.wire import ProcessError, DataError

from apps.bitcoin.sign_tx.bitcoinlike import Bitcoinlike
from apps.bitcoin.sign_tx import approvers
from apps.common.writers import (
    write_compact_size,
    write_uint32_le,
)

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Sequence, Tuple
    from apps.common.coininfo import CoinInfo
    from apps.bitcoin.sign_tx.tx_info import OriginalTxInfo, TxInfo
    from apps.bitcoin.writers import Writer
    from apps.bitcoin.sign_tx.sig_hasher import SigHasher
    from trezor.utils import HashWriter
    from trezor.messages import PrevTx, SignTx, TxInput, TxOutput, TxAckInput, TxAckOutput

OVERWINTERED = const(0x8000_0000)

class Zcash(Bitcoinlike):
    def __init__(
        self,
        tx: SignTx,
        keychain: Tuple[Keychain, OrchardKeychain],
        coin: CoinInfo,
        approver: ZcashApprover,
    ) -> None:
        ensure(coin.overwintered)
        if tx.version != 5:
            log.warning(__name__, "Transaction format version {} is not supported.".format(tx.version))
            log.warning(__name__, "Switching to version 5.".format(tx.version))
            tx.version = 5

        super().__init__(tx, keychain[0], coin, approver)

        self.tx_info.sig_hasher.initialize(self.tx_info.tx)

        self.orchard = OrchardSigner(
            self.tx_info,
            keychain[1],
            approver,
            coin,
            self.tx_req,
        )

    def create_sig_hasher(self) -> SigHasher:
        return ZcashExtendedSigHasher()

    def create_hash_writer(self) -> HashWriter:
        # TODO: add limited support for transparent replacement transactions
        raise NotImplementedError

    async def step1_process_inputs(self):
        await super().step1_process_inputs()
        await self.orchard.process_flags()
        await self.orchard.process_inputs()

    async def step2_approve_outputs(self):
        await super().step2_approve_outputs()
        await self.orchard.approve_outputs()

    async def step3_verify_inputs(self):
        if self.orig_txs:
            raise ProcessError("Replacement transactions are not supported.")

        # We don't check prevouts, because BIP-341 techniques
        # were adapted in ZIP-244 sighash algortihm.
        # see: https://github.com/zcash/zips/issues/574
        self.taproot_only = True  # turn on taproot behavior
        await super().step3_verify_inputs()
        self.taproot_only = False  # turn off taproot behavior

    async def step4_serialize_inputs(self):
        # shield actions first to get a sighash
        await self.orchard.compute_digest()
        await super().step4_serialize_inputs()

    async def step5_serialize_outputs(self):
        await super().step5_serialize_outputs()
        await self.serialize_empty_sapling_bundle()
        # orchard serialization is up to the client

    async def step6_sign_segwit_inputs(self):
        # transparent inputs were signed in step 4
        await self.orchard.sign_inputs()

    async def sign_nonsegwit_input(self, i_sign: int) -> None:
        await self.sign_nonsegwit_bip143_input(i_sign)

    async def serialize_empty_sapling_bundle(self):
        write_compact_size(self.serialized_tx, 0)  # nSpendsSapling
        write_compact_size(self.serialized_tx, 0)  # nOutputsSapling

    def write_tx_header(
        self, w: Writer, tx: SignTx | PrevTx, witness_marker: bool
    ) -> None:
        if tx.version_group_id is None:
            raise DataError("Version group ID is missing")
        assert tx.expiry is not None # checked in sanitize_*

        # defined in ZIP-225 (see https://zips.z.cash/zip-0225)
        write_uint32_le(w, tx.version | OVERWINTERED)  # nVersion | fOverwintered
        write_uint32_le(w, tx.version_group_id)        # nVersionGroupId
        write_uint32_le(w, tx.branch_id)               # nConsensusBranchId
        write_uint32_le(w, tx.lock_time)               # lock_time
        write_uint32_le(w, tx.expiry)                  # expiryHeight

    def write_tx_footer(self, w: Writer, tx: SignTx | PrevTx):
        pass  # no footer (see https://zips.z.cash/zip-0225)


class ZcashApprover(approvers.BasicApprover):
    def __init__(self, *args, **kwargs):
        self.orchard_balance = 0
        super().__init__(*args, **kwargs)

    def add_orchard_input(self, txi: ZcashOrchardInput) -> None:
        self.total_in += txi.amount
        self.orchard_balance += txi.amount

    def add_orchard_change_output(self, txo: ZcashOrchardOutput) -> None:
        self.change_count += 1
        self.total_out += txo.amount
        self.change_out += txo.amount
        self.orchard_balance -= txo.amount

    async def add_orchard_external_output(self, txo: ZcashOrchardOutput) -> None:
        self.total_out += txo.amount
        self.orchard_balance -= txo.amount
        yield UiConfirmOrchardOutput(txo)


class ZcashExtendedSigHasher(sig_hasher.ZcashSigHasher):
    """
    This class adds `SigHasher` interface for `ZcashSigHasher` class.
    """

    def add_input(self, txi: TxInput, script_pubkey: bytes):
        self.transparent.add_input(txi, script_pubkey)

    def add_output(self, txo: TxOutput, script_pubkey: bytes):
        self.transparent.add_output(txo, script_pubkey)

    def hash143(
        self,
        txi: TxInput,
        public_keys: Sequence[bytes | memoryview],
        threshold: int,
        tx: SignTx | PrevTx,
        coin: coininfo.CoinInfo,
        hash_type: int,
    ) -> bytes:
        if not self.initialized:
            self.initialize(tx)
        txin_sig_digest = sig_hasher.get_txin_sig_digest(
            txi, public_keys, threshold, coin, hash_type,
        )
        return self.signature_digest(txin_sig_digest)

    def hash341(
        self,
        i: int,
        tx: SignTx | PrevTx,
        sighash_type: SigHashType,
    ) -> bytes:
        raise NotImplementedError

