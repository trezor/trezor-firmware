from micropython import const
from typing import TYPE_CHECKING

from trezor.crypto.hashlib import blake256
from trezor.enums import InputScriptType
from trezor.utils import HashWriter
from trezor.wire import DataError, ProcessError

from apps.bitcoin.sign_tx.tx_weight import TxWeightCalculator
from apps.common.writers import write_compact_size

from .. import scripts_decred, writers
from ..common import ecdsa_hash_pubkey
from ..writers import write_uint32
from . import helpers
from .approvers import BasicApprover
from .bitcoin import Bitcoin
from .progress import progress

_DECRED_SERIALIZE_FULL = const(0 << 16)
_DECRED_SERIALIZE_NO_WITNESS = const(1 << 16)
_DECRED_SERIALIZE_WITNESS_SIGNING = const(3 << 16)
_DECRED_SCRIPT_VERSION = const(0)
OUTPUT_SCRIPT_NULL_SSTXCHANGE = (
    b"\xBD\x76\xA9\x14\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x88\xAC"
)

if TYPE_CHECKING:
    from typing import Sequence

    from trezor.crypto import bip32
    from trezor.messages import PrevInput, PrevOutput, PrevTx, SignTx, TxInput, TxOutput

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain

    from ..common import SigHashType
    from ..writers import Writer
    from . import approvers
    from .sig_hasher import SigHasher


# Decred input size (without script): 32 prevhash, 4 idx, 1 Decred tree, 4 sequence
_TXSIZE_DECRED_INPUT = const(41)

# Decred script version: 2 bytes
_TXSIZE_DECRED_SCRIPT_VERSION = const(2)

# Decred expiry size: 4 bytes in footer
_TXSIZE_DECRED_EXPIRY = const(4)

# Decred witness size (without script): 8 byte amount, 4 byte block height, 4 byte block index
_TXSIZE_DECRED_WITNESS = const(16)


class DecredTxWeightCalculator(TxWeightCalculator):
    def get_base_weight(self) -> int:
        base_weight = super().get_base_weight()
        base_weight += 4 * _TXSIZE_DECRED_EXPIRY
        # Add witness input count.
        base_weight += 4 * self.compact_size_len(self.inputs_count)
        return base_weight

    def add_input(self, i: TxInput) -> None:
        self.inputs_count += 1

        # Input.
        self.counter += 4 * _TXSIZE_DECRED_INPUT

        # Input witness.
        input_script_size = self.input_script_size(i)
        if i.script_type == InputScriptType.SPENDMULTISIG:
            # Decred fixed the the OP_FALSE bug in multisig.
            input_script_size -= 1  # Subtract one OP_FALSE byte.

        self.counter += 4 * _TXSIZE_DECRED_WITNESS
        self.counter += 4 * self.compact_size_len(input_script_size)
        self.counter += 4 * input_script_size

    def add_output(self, script: bytes) -> None:
        super().add_output(script)
        self.counter += 4 * _TXSIZE_DECRED_SCRIPT_VERSION


class DecredApprover(BasicApprover):
    def __init__(self, tx: SignTx, coin: CoinInfo) -> None:
        super().__init__(tx, coin)
        self.weight = DecredTxWeightCalculator()

    async def add_decred_sstx_submission(
        self, txo: TxOutput, script_pubkey: bytes
    ) -> None:
        # NOTE: The following calls Approver.add_external_output(), not BasicApprover.add_external_output().
        # This is needed to skip calling helpers.confirm_output(), which is what BasicApprover would do.
        await super(BasicApprover, self).add_external_output(txo, script_pubkey, None)
        await helpers.confirm_decred_sstx_submission(txo, self.coin, self.amount_unit)


class DecredSigHasher:
    def __init__(self, h_prefix: HashWriter) -> None:
        self.h_prefix = h_prefix

    def add_input(self, txi: TxInput, script_pubkey: bytes) -> None:
        Decred.write_tx_input(self.h_prefix, txi, bytes())

    def add_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        Decred.write_tx_output(self.h_prefix, txo, script_pubkey)

    def hash143(
        self,
        txi: TxInput,
        public_keys: Sequence[bytes | memoryview],
        threshold: int,
        tx: SignTx | PrevTx,
        coin: CoinInfo,
        hash_type: int,
    ) -> bytes:
        raise NotImplementedError

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


class Decred(Bitcoin):
    def __init__(
        self,
        tx: SignTx,
        keychain: Keychain,
        coin: CoinInfo,
        approver: approvers.Approver | None,
    ) -> None:
        from trezor.utils import ensure

        ensure(coin.decred)
        self.h_prefix = HashWriter(blake256())

        ensure(approver is None)
        approver = DecredApprover(tx, coin)
        super().__init__(tx, keychain, coin, approver)

        tx = self.tx_info.tx  # local_cache_attribute

        if self.serialize:
            self.write_tx_header(self.serialized_tx, tx, witness_marker=True)
            write_compact_size(self.serialized_tx, tx.inputs_count)

        write_uint32(self.h_prefix, tx.version | _DECRED_SERIALIZE_NO_WITNESS)
        write_compact_size(self.h_prefix, tx.inputs_count)

    def create_hash_writer(self) -> HashWriter:
        return HashWriter(blake256())

    def create_sig_hasher(self, tx: SignTx | PrevTx) -> SigHasher:
        return DecredSigHasher(self.h_prefix)

    async def step2_approve_outputs(self) -> None:
        tx = self.tx_info.tx  # local_cache_attribute

        write_compact_size(self.h_prefix, tx.outputs_count)
        if self.serialize:
            write_compact_size(self.serialized_tx, tx.outputs_count)

        if tx.decred_staking_ticket:
            await self.approve_staking_ticket()
        else:
            await super().step2_approve_outputs()

        self.write_tx_footer(self.h_prefix, tx)
        if self.serialize:
            self.write_tx_footer(self.serialized_tx, tx)

    async def process_internal_input(self, txi: TxInput, node: bip32.HDNode) -> None:
        await super().process_internal_input(txi, node)

        # Decred serializes inputs early.
        if self.serialize:
            self.write_tx_input(self.serialized_tx, txi, bytes())

    async def process_external_input(self, txi: TxInput) -> None:
        raise DataError("External inputs not supported")

    async def process_original_input(self, txi: TxInput, script_pubkey: bytes) -> None:
        raise DataError("Replacement transactions not supported")

    async def approve_output(
        self,
        txo: TxOutput,
        script_pubkey: bytes,
        orig_txo: TxOutput | None,
    ) -> None:
        await super().approve_output(txo, script_pubkey, orig_txo)
        if self.serialize:
            self.write_tx_output(self.serialized_tx, txo, script_pubkey)

    async def step4_serialize_inputs(self) -> None:
        from trezor.enums import DecredStakingSpendType

        from .. import multisig
        from ..common import SigHashType, ecdsa_sign
        from .progress import progress

        inputs_count = self.tx_info.tx.inputs_count  # local_cache_attribute
        coin = self.coin  # local_cache_attribute

        if self.serialize:
            write_compact_size(self.serialized_tx, inputs_count)

        prefix_hash = self.h_prefix.get_digest()

        for i_sign in range(inputs_count):
            progress.advance()

            txi_sign = await helpers.request_tx_input(self.tx_req, i_sign, coin)

            self.tx_info.check_input(txi_sign)

            key_sign = self.keychain.derive(txi_sign.address_n)
            key_sign_pub = key_sign.public_key()

            h_witness = self.create_hash_writer()
            write_uint32(
                h_witness, self.tx_info.tx.version | _DECRED_SERIALIZE_WITNESS_SIGNING
            )
            write_compact_size(h_witness, inputs_count)

            for ii in range(inputs_count):
                if ii == i_sign:
                    if txi_sign.decred_staking_spend == DecredStakingSpendType.SSRTX:
                        scripts_decred.write_output_script_ssrtx_prefixed(
                            h_witness, ecdsa_hash_pubkey(key_sign_pub, coin)
                        )
                    elif txi_sign.decred_staking_spend == DecredStakingSpendType.SSGen:
                        scripts_decred.write_output_script_ssgen_prefixed(
                            h_witness, ecdsa_hash_pubkey(key_sign_pub, coin)
                        )
                    elif txi_sign.script_type == InputScriptType.SPENDMULTISIG:
                        assert txi_sign.multisig is not None
                        scripts_decred.write_output_script_multisig(
                            h_witness,
                            multisig.multisig_get_pubkeys(txi_sign.multisig),
                            txi_sign.multisig.m,
                            prefixed=True,
                        )
                    elif txi_sign.script_type == InputScriptType.SPENDADDRESS:
                        scripts_decred.write_output_script_p2pkh(
                            h_witness,
                            ecdsa_hash_pubkey(key_sign_pub, coin),
                            prefixed=True,
                        )
                    else:
                        raise DataError("Unsupported input script type")
                else:
                    write_compact_size(h_witness, 0)

            witness_hash = writers.get_tx_hash(
                h_witness, double=coin.sign_hash_double, reverse=False
            )

            h_sign = self.create_hash_writer()
            write_uint32(h_sign, SigHashType.SIGHASH_ALL)
            writers.write_bytes_fixed(h_sign, prefix_hash, writers.TX_HASH_SIZE)
            writers.write_bytes_fixed(h_sign, witness_hash, writers.TX_HASH_SIZE)

            sig_hash = writers.get_tx_hash(h_sign, double=coin.sign_hash_double)
            signature = ecdsa_sign(key_sign, sig_hash)

            # serialize input with correct signature
            self.set_serialized_signature(i_sign, signature)
            if self.serialize:
                self.write_tx_input_witness(
                    self.serialized_tx, txi_sign, key_sign_pub, signature
                )

    async def step5_serialize_outputs(self) -> None:
        pass

    async def step6_sign_segwit_inputs(self) -> None:
        pass

    async def step7_finish(self) -> None:
        if __debug__:
            progress.assert_finished()

        await helpers.request_tx_finish(self.tx_req)

    def check_prevtx_output(self, txo_bin: PrevOutput) -> None:
        if txo_bin.decred_script_version != 0:
            raise ProcessError("Cannot use utxo that has script_version != 0")

    @staticmethod
    def write_tx_input(
        w: Writer,
        txi: TxInput | PrevInput,
        script: bytes,
    ) -> None:
        writers.write_bytes_reversed(w, txi.prev_hash, writers.TX_HASH_SIZE)
        write_uint32(w, txi.prev_index or 0)
        writers.write_uint8(w, txi.decred_tree or 0)
        write_uint32(w, txi.sequence)

    @staticmethod
    def write_tx_output(
        w: Writer,
        txo: TxOutput | PrevOutput,
        script_pubkey: bytes,
    ) -> None:
        from trezor.messages import PrevOutput

        writers.write_uint64(w, txo.amount)
        if PrevOutput.is_type_of(txo):
            if txo.decred_script_version is None:
                raise DataError("Script version must be provided")
            writers.write_uint16(w, txo.decred_script_version)
        else:
            writers.write_uint16(w, _DECRED_SCRIPT_VERSION)
        writers.write_bytes_prefixed(w, script_pubkey)

    def process_sstx_commitment_owned(self, txo: TxOutput) -> bytearray:
        if not self.tx_info.output_is_change(txo):
            raise DataError("Invalid sstxcommitment path.")
        node = self.keychain.derive(txo.address_n)
        pkh = ecdsa_hash_pubkey(node.public_key(), self.coin)
        op_return_data = scripts_decred.sstxcommitment_pkh(pkh, txo.amount)
        txo.amount = 0  # Clear the amount, since this is an OP_RETURN.
        return scripts_decred.output_script_paytoopreturn(op_return_data)

    async def approve_staking_ticket(self) -> None:
        approver = self.approver  # local_cache_attribute
        tx_info = self.tx_info  # local_cache_attribute

        assert isinstance(approver, DecredApprover)

        if tx_info.tx.outputs_count != 3:
            raise DataError("Ticket has wrong number of outputs.")

        # SSTX submission
        progress.advance()
        txo = await helpers.request_tx_output(self.tx_req, 0, self.coin)
        if txo.address is None:
            raise DataError("Missing address.")
        script_pubkey = scripts_decred.output_script_sstxsubmissionpkh(txo.address)
        await approver.add_decred_sstx_submission(txo, script_pubkey)
        tx_info.add_output(txo, script_pubkey)
        if self.serialize:
            self.write_tx_output(self.serialized_tx, txo, script_pubkey)

        # SSTX commitment
        progress.advance()
        txo = await helpers.request_tx_output(self.tx_req, 1, self.coin)
        if txo.amount != approver.total_in:
            raise DataError("Wrong sstxcommitment amount.")
        script_pubkey = self.process_sstx_commitment_owned(txo)
        await approver.add_change_output(txo, script_pubkey)
        tx_info.add_output(txo, script_pubkey)
        if self.serialize:
            self.write_tx_output(self.serialized_tx, txo, script_pubkey)

        # SSTX change
        progress.advance()
        txo = await helpers.request_tx_output(self.tx_req, 2, self.coin)
        if txo.address is None:
            raise DataError("Missing address.")
        script_pubkey = scripts_decred.output_script_sstxchange(txo.address)
        # Using change addresses is no longer common practice. Inputs are split
        # beforehand and should be exact. SSTX change should pay zero amount to
        # a zeroed hash.
        if txo.amount != 0:
            raise DataError("Only value of 0 allowed for sstx change.")
        if script_pubkey != OUTPUT_SCRIPT_NULL_SSTXCHANGE:
            raise DataError("Only zeroed addresses accepted for sstx change.")
        # nothing to approve, just add to tx_weight
        await approver._add_output(txo, script_pubkey)
        tx_info.add_output(txo, script_pubkey)
        if self.serialize:
            self.write_tx_output(self.serialized_tx, txo, script_pubkey)

    def write_tx_header(
        self,
        w: Writer,
        tx: SignTx | PrevTx,
        witness_marker: bool,
    ) -> None:
        # The upper 16 bits of the transaction version specify the serialization
        # format and the lower 16 bits specify the version number.
        if witness_marker:
            version = tx.version | _DECRED_SERIALIZE_FULL
        else:
            version = tx.version | _DECRED_SERIALIZE_NO_WITNESS

        write_uint32(w, version)

    def write_tx_footer(self, w: Writer, tx: SignTx | PrevTx) -> None:
        assert tx.expiry is not None  # checked in sanitize_*
        write_uint32(w, tx.lock_time)
        write_uint32(w, tx.expiry)

    def write_tx_input_witness(
        self, w: Writer, txi: TxInput, pubkey: bytes, signature: bytes
    ) -> None:
        writers.write_uint64(w, txi.amount)
        write_uint32(w, 0)  # block height fraud proof
        write_uint32(w, 0xFFFF_FFFF)  # block index fraud proof
        scripts_decred.write_input_script_prefixed(
            w,
            txi.script_type,
            txi.multisig,
            self.coin,
            self.get_sighash_type(txi),
            pubkey,
            signature,
        )
