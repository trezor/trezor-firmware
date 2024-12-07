from micropython import const
from typing import TYPE_CHECKING

from .. import writers

if TYPE_CHECKING:
    from typing import Protocol

    from trezor.messages import PrevTx, SignTx, TxInput, TxOutput
    from trezor.utils import HashWriter

    from apps.common.coininfo import CoinInfo

    from .sig_hasher import SigHasher

    class Signer(Protocol):
        coin: CoinInfo

        def create_hash_writer(self) -> HashWriter: ...

        def create_sig_hasher(self, tx: SignTx | PrevTx) -> SigHasher: ...

        def write_tx_header(
            self,
            w: writers.Writer,
            tx: SignTx | PrevTx,
            witness_marker: bool,
        ) -> None: ...

        async def write_prev_tx_footer(
            self, w: writers.Writer, tx: PrevTx, prev_hash: bytes
        ) -> None: ...


# Setting nSequence to this value for every input in a transaction disables nLockTime.
_SEQUENCE_FINAL = const(0xFFFF_FFFF)

# Setting nSequence to a value greater than this for every input in a transaction
# disables replace-by-fee opt-in.
_MAX_BIP125_RBF_SEQUENCE = const(0xFFFF_FFFD)


class TxInfoBase:
    def __init__(self, signer: Signer, tx: SignTx | PrevTx) -> None:
        from trezor.crypto.hashlib import sha256
        from trezor.utils import HashWriter

        from .change_detector import ChangeDetector

        self.change_detector = ChangeDetector()

        # h_tx_check is used to make sure that the inputs and outputs streamed in
        # different steps are the same every time, e.g. the ones streamed for approval
        # in Steps 1 and 2 and the ones streamed for signing legacy inputs in Step 4.
        self.h_tx_check = HashWriter(sha256())  # not a real tx hash

        # The digests of the inputs streamed for approval in Step 1. These are used to
        # ensure that the inputs streamed for verification in Step 3 are the same as
        # those in Step 1.
        self.h_inputs_check: bytes | None = None

        # BIP-0143 transaction hashing.
        self.sig_hasher = signer.create_sig_hasher(tx)

        # The minimum nSequence of all inputs.
        self.min_sequence = _SEQUENCE_FINAL

    def add_input(self, txi: TxInput, script_pubkey: bytes) -> None:
        # all inputs are included (non-segwit as well)
        self.sig_hasher.add_input(txi, script_pubkey)
        writers.write_tx_input_check(self.h_tx_check, txi)
        self.min_sequence = min(self.min_sequence, txi.sequence)
        self.change_detector.add_input(txi)

    def add_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        self.sig_hasher.add_output(txo, script_pubkey)
        writers.write_tx_output(self.h_tx_check, txo, script_pubkey)

    def check_input(self, txi: TxInput) -> None:
        self.change_detector.check_input(txi)

    def output_is_change(self, txo: TxOutput) -> bool:
        return self.change_detector.output_is_change(txo)

    def lock_time_disabled(self) -> bool:
        return self.min_sequence == _SEQUENCE_FINAL

    def rbf_disabled(self) -> bool:
        return self.min_sequence > _MAX_BIP125_RBF_SEQUENCE

    def get_tx_check_digest(self) -> bytes:
        return self.h_tx_check.get_digest()


# Used to keep track of the transaction currently being signed.
class TxInfo(TxInfoBase):
    def __init__(self, signer: Signer, tx: SignTx) -> None:
        super().__init__(signer, tx)
        self.tx = tx


# Used to keep track of any original transactions which are being replaced by the current transaction.
class OriginalTxInfo(TxInfoBase):
    def __init__(self, signer: Signer, tx: PrevTx, orig_hash: bytes) -> None:
        super().__init__(signer, tx)
        self.tx = tx
        self.signer = signer
        self.orig_hash = orig_hash

        # Index of the next input or output to be added by add_input or add_output. Signer uses this
        # value to check that original transaction inputs and outputs are streamed in order, and to
        # check whether any have been skipped. Incrementing and resetting this variable is the
        # responsibility of the signer class.
        self.index = 0

        # Transaction hasher to compute the TXID.
        self.h_tx = signer.create_hash_writer()
        signer.write_tx_header(self.h_tx, tx, witness_marker=False)
        writers.write_compact_size(self.h_tx, tx.inputs_count)

    def add_input(self, txi: TxInput, script_pubkey: bytes) -> None:
        super().add_input(txi, script_pubkey)
        writers.write_tx_input(self.h_tx, txi, txi.script_sig or bytes())

    def add_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        super().add_output(txo, script_pubkey)

        if self.index == 0:
            writers.write_compact_size(self.h_tx, self.tx.outputs_count)

        writers.write_tx_output(self.h_tx, txo, script_pubkey)

    async def finalize_tx_hash(self) -> None:
        from trezor import wire

        await self.signer.write_prev_tx_footer(self.h_tx, self.tx, self.orig_hash)
        if self.orig_hash != writers.get_tx_hash(
            self.h_tx, double=self.signer.coin.sign_hash_double, reverse=True
        ):
            # This may happen if incorrect information is supplied in the TXORIGINPUT
            # or TXORIGOUTPUT responses or if the device is loaded with the wrong seed,
            # because we derive the scriptPubKeys of change-outputs from the seed using
            # the provided path.
            raise wire.ProcessError("Invalid original TXID.")
