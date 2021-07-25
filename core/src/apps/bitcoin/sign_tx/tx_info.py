from micropython import const

from trezor import wire
from trezor.crypto.hashlib import sha256
from trezor.utils import HashWriter

from .. import common, writers
from ..common import BIP32_WALLET_DEPTH, input_is_external
from .matchcheck import MultisigFingerprintChecker, WalletPathChecker

if False:
    from typing import Protocol
    from trezor.messages import (
        PrevInput,
        PrevOutput,
        PrevTx,
        SignTx,
        TxInput,
        TxOutput,
    )
    from .hash143 import Hash143

    from apps.common.coininfo import CoinInfo

    class Signer(Protocol):
        coin = ...  # type: CoinInfo

        def create_hash_writer(self) -> HashWriter:
            ...

        def create_hash143(self) -> Hash143:
            ...

        def write_tx_header(
            self,
            w: writers.Writer,
            tx: SignTx | PrevTx,
            witness_marker: bool,
        ) -> None:
            ...

        @staticmethod
        def write_tx_input(
            w: writers.Writer,
            txi: TxInput | PrevInput,
            script: bytes,
        ) -> None:
            ...

        @staticmethod
        def write_tx_output(
            w: writers.Writer,
            txo: TxOutput | PrevOutput,
            script_pubkey: bytes,
        ) -> None:
            ...

        async def write_prev_tx_footer(
            self, w: writers.Writer, tx: PrevTx, prev_hash: bytes
        ) -> None:
            ...


# The chain id used for change.
_BIP32_CHANGE_CHAIN = const(1)

# The maximum allowed change address. This should be large enough for normal
# use and still allow to quickly brute-force the correct BIP32 path.
_BIP32_MAX_LAST_ELEMENT = const(1_000_000)

# Setting nSequence to this value for every input in a transaction disables nLockTime.
_SEQUENCE_FINAL = const(0xFFFF_FFFF)

# Setting nSequence to a value greater than this for every input in a transaction
# disables replace-by-fee opt-in.
_MAX_BIP125_RBF_SEQUENCE = const(0xFFFF_FFFD)


class TxInfoBase:
    def __init__(self, signer: Signer) -> None:
        # Checksum of multisig inputs, used to validate change-output.
        self.multisig_fingerprint = MultisigFingerprintChecker()

        # Common prefix of input paths, used to validate change-output.
        self.wallet_path = WalletPathChecker()

        # h_tx_check is used to make sure that the inputs and outputs streamed in
        # different steps are the same every time, e.g. the ones streamed for approval
        # in Steps 1 and 2 and the ones streamed for signing legacy inputs in Step 4.
        self.h_tx_check = HashWriter(sha256())  # not a real tx hash

        # BIP-0143 transaction hashing.
        self.hash143 = signer.create_hash143()

        # The minimum nSequence of all inputs.
        self.min_sequence = _SEQUENCE_FINAL

    def add_input(self, txi: TxInput) -> None:
        self.hash143.add_input(txi)  # all inputs are included (non-segwit as well)
        writers.write_tx_input_check(self.h_tx_check, txi)
        self.min_sequence = min(self.min_sequence, txi.sequence)

        if not input_is_external(txi):
            self.wallet_path.add_input(txi)
            self.multisig_fingerprint.add_input(txi)

    def add_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        self.hash143.add_output(txo, script_pubkey)
        writers.write_tx_output(self.h_tx_check, txo, script_pubkey)

    def check_input(self, txi: TxInput) -> None:
        self.wallet_path.check_input(txi)
        self.multisig_fingerprint.check_input(txi)

    def output_is_change(self, txo: TxOutput) -> bool:
        if txo.script_type not in common.CHANGE_OUTPUT_SCRIPT_TYPES:
            return False
        if txo.multisig and not self.multisig_fingerprint.output_matches(txo):
            return False
        return (
            self.wallet_path.output_matches(txo)
            and len(txo.address_n) >= BIP32_WALLET_DEPTH
            and txo.address_n[-2] <= _BIP32_CHANGE_CHAIN
            and txo.address_n[-1] <= _BIP32_MAX_LAST_ELEMENT
            and txo.amount > 0
        )

    def lock_time_disabled(self) -> bool:
        return self.min_sequence == _SEQUENCE_FINAL

    def rbf_disabled(self) -> bool:
        return self.min_sequence > _MAX_BIP125_RBF_SEQUENCE

    def get_tx_check_digest(self) -> bytes:
        return self.h_tx_check.get_digest()


# Used to keep track of the transaction currently being signed.
class TxInfo(TxInfoBase):
    def __init__(self, signer: Signer, tx: SignTx) -> None:
        super().__init__(signer)
        self.tx = tx


# Used to keep track of any original transactions which are being replaced by the current transaction.
class OriginalTxInfo(TxInfoBase):
    def __init__(self, signer: Signer, tx: PrevTx, orig_hash: bytes) -> None:
        super().__init__(signer)
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
        writers.write_bitcoin_varint(self.h_tx, tx.inputs_count)

        # The input which will be used for verification and its index in the original transaction.
        self.verification_input: TxInput | None = None
        self.verification_index: int | None = None

    def add_input(self, txi: TxInput) -> None:
        super().add_input(txi)
        self.signer.write_tx_input(self.h_tx, txi, txi.script_sig or bytes())

        # For verification use the first original input that specifies address_n.
        if not self.verification_input and txi.address_n:
            self.verification_input = txi
            self.verification_index = self.index

    def add_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        super().add_output(txo, script_pubkey)

        if self.index == 0:
            writers.write_bitcoin_varint(self.h_tx, self.tx.outputs_count)

        self.signer.write_tx_output(self.h_tx, txo, script_pubkey)

    async def finalize_tx_hash(self) -> None:
        await self.signer.write_prev_tx_footer(self.h_tx, self.tx, self.orig_hash)
        if self.orig_hash != writers.get_tx_hash(
            self.h_tx, double=self.signer.coin.sign_hash_double, reverse=True
        ):
            # This may happen if incorrect information is supplied in the TXORIGINPUT
            # or TXORIGOUTPUT responses or if the device is loaded with the wrong seed,
            # because we derive the scriptPubKeys of change-outputs from the seed using
            # the provided path.
            raise wire.ProcessError("Invalid original TXID.")
