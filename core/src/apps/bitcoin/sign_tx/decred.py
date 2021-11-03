from micropython import const

from trezor import wire
from trezor.crypto.hashlib import blake256
from trezor.enums import DecredStakingSpendType, InputScriptType
from trezor.messages import PrevOutput
from trezor.utils import HashWriter, ensure

from apps.common.writers import write_bitcoin_varint

from .. import multisig, scripts_decred, writers
from ..common import ecdsa_hash_pubkey, ecdsa_sign
from . import approvers, helpers, progress
from .approvers import BasicApprover
from .bitcoin import Bitcoin

DECRED_SERIALIZE_FULL = const(0 << 16)
DECRED_SERIALIZE_NO_WITNESS = const(1 << 16)
DECRED_SERIALIZE_WITNESS_SIGNING = const(3 << 16)
DECRED_SCRIPT_VERSION = const(0)
DECRED_SIGHASH_ALL = const(1)
OUTPUT_SCRIPT_NULL_SSTXCHANGE = (
    b"\xBD\x76\xA9\x14\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x88\xAC"
)

if False:
    from typing import Sequence

    from trezor.messages import (
        SignTx,
        TxInput,
        TxOutput,
        PrevTx,
        PrevInput,
    )

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain

    from .sig_hasher import SigHasher


class DecredApprover(BasicApprover):
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
        sighash_type: int,
    ) -> bytes:
        raise NotImplementedError

    def hash341(
        self,
        i: int,
        tx: SignTx | PrevTx,
        sighash_type: int,
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
        ensure(coin.decred)
        self.h_prefix = HashWriter(blake256())

        ensure(approver is None)
        approver = DecredApprover(tx, coin)
        super().__init__(tx, keychain, coin, approver)

        self.write_tx_header(self.serialized_tx, self.tx_info.tx, witness_marker=True)
        write_bitcoin_varint(self.serialized_tx, self.tx_info.tx.inputs_count)

        writers.write_uint32(
            self.h_prefix, self.tx_info.tx.version | DECRED_SERIALIZE_NO_WITNESS
        )
        write_bitcoin_varint(self.h_prefix, self.tx_info.tx.inputs_count)

    def create_hash_writer(self) -> HashWriter:
        return HashWriter(blake256())

    def create_sig_hasher(self) -> SigHasher:
        return DecredSigHasher(self.h_prefix)

    async def step2_approve_outputs(self) -> None:
        write_bitcoin_varint(self.serialized_tx, self.tx_info.tx.outputs_count)
        write_bitcoin_varint(self.h_prefix, self.tx_info.tx.outputs_count)

        if self.tx_info.tx.decred_staking_ticket:
            await self.approve_staking_ticket()
        else:
            await super().step2_approve_outputs()

        self.write_tx_footer(self.serialized_tx, self.tx_info.tx)
        self.write_tx_footer(self.h_prefix, self.tx_info.tx)

    async def process_internal_input(self, txi: TxInput) -> None:
        await super().process_internal_input(txi)

        # Decred serializes inputs early.
        self.write_tx_input(self.serialized_tx, txi, bytes())

    async def process_external_input(self, txi: TxInput) -> None:
        raise wire.DataError("External inputs not supported")

    async def process_original_input(self, txi: TxInput, script_pubkey: bytes) -> None:
        raise wire.DataError("Replacement transactions not supported")

    async def approve_output(
        self,
        txo: TxOutput,
        script_pubkey: bytes,
        orig_txo: TxOutput | None,
    ) -> None:
        await super().approve_output(txo, script_pubkey, orig_txo)
        self.write_tx_output(self.serialized_tx, txo, script_pubkey)

    async def step4_serialize_inputs(self) -> None:
        write_bitcoin_varint(self.serialized_tx, self.tx_info.tx.inputs_count)

        prefix_hash = self.h_prefix.get_digest()

        for i_sign in range(self.tx_info.tx.inputs_count):
            progress.advance()

            txi_sign = await helpers.request_tx_input(self.tx_req, i_sign, self.coin)

            self.tx_info.check_input(txi_sign)

            key_sign = self.keychain.derive(txi_sign.address_n)
            key_sign_pub = key_sign.public_key()

            h_witness = self.create_hash_writer()
            writers.write_uint32(
                h_witness, self.tx_info.tx.version | DECRED_SERIALIZE_WITNESS_SIGNING
            )
            write_bitcoin_varint(h_witness, self.tx_info.tx.inputs_count)

            for ii in range(self.tx_info.tx.inputs_count):
                if ii == i_sign:
                    if txi_sign.decred_staking_spend == DecredStakingSpendType.SSRTX:
                        scripts_decred.write_output_script_ssrtx_prefixed(
                            h_witness, ecdsa_hash_pubkey(key_sign_pub, self.coin)
                        )
                    elif txi_sign.decred_staking_spend == DecredStakingSpendType.SSGen:
                        scripts_decred.write_output_script_ssgen_prefixed(
                            h_witness, ecdsa_hash_pubkey(key_sign_pub, self.coin)
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
                            ecdsa_hash_pubkey(key_sign_pub, self.coin),
                            prefixed=True,
                        )
                    else:
                        raise wire.DataError("Unsupported input script type")
                else:
                    write_bitcoin_varint(h_witness, 0)

            witness_hash = writers.get_tx_hash(
                h_witness, double=self.coin.sign_hash_double, reverse=False
            )

            h_sign = self.create_hash_writer()
            writers.write_uint32(h_sign, DECRED_SIGHASH_ALL)
            writers.write_bytes_fixed(h_sign, prefix_hash, writers.TX_HASH_SIZE)
            writers.write_bytes_fixed(h_sign, witness_hash, writers.TX_HASH_SIZE)

            sig_hash = writers.get_tx_hash(h_sign, double=self.coin.sign_hash_double)
            signature = ecdsa_sign(key_sign, sig_hash)

            # serialize input with correct signature
            self.write_tx_input_witness(
                self.serialized_tx, txi_sign, key_sign_pub, signature
            )
            self.set_serialized_signature(i_sign, signature)

    async def step5_serialize_outputs(self) -> None:
        pass

    async def step6_sign_segwit_inputs(self) -> None:
        pass

    async def step7_finish(self) -> None:
        await helpers.request_tx_finish(self.tx_req)

    def check_prevtx_output(self, txo_bin: PrevOutput) -> None:
        if txo_bin.decred_script_version != 0:
            raise wire.ProcessError("Cannot use utxo that has script_version != 0")

    @staticmethod
    def write_tx_input(
        w: writers.Writer,
        txi: TxInput | PrevInput,
        script: bytes,
    ) -> None:
        writers.write_bytes_reversed(w, txi.prev_hash, writers.TX_HASH_SIZE)
        writers.write_uint32(w, txi.prev_index or 0)
        writers.write_uint8(w, txi.decred_tree or 0)
        writers.write_uint32(w, txi.sequence)

    @staticmethod
    def write_tx_output(
        w: writers.Writer,
        txo: TxOutput | PrevOutput,
        script_pubkey: bytes,
    ) -> None:
        writers.write_uint64(w, txo.amount)
        if PrevOutput.is_type_of(txo):
            if txo.decred_script_version is None:
                raise wire.DataError("Script version must be provided")
            writers.write_uint16(w, txo.decred_script_version)
        else:
            writers.write_uint16(w, DECRED_SCRIPT_VERSION)
        writers.write_bytes_prefixed(w, script_pubkey)

    def process_sstx_commitment_owned(self, txo: TxOutput) -> bytearray:
        if not self.tx_info.output_is_change(txo):
            raise wire.DataError("Invalid sstxcommitment path.")
        node = self.keychain.derive(txo.address_n)
        pkh = ecdsa_hash_pubkey(node.public_key(), self.coin)
        op_return_data = scripts_decred.sstxcommitment_pkh(pkh, txo.amount)
        txo.amount = 0  # Clear the amount, since this is an OP_RETURN.
        return scripts_decred.output_script_paytoopreturn(op_return_data)

    async def approve_staking_ticket(self) -> None:
        assert isinstance(self.approver, DecredApprover)

        if self.tx_info.tx.outputs_count != 3:
            raise wire.DataError("Ticket has wrong number of outputs.")

        # SSTX submission
        txo = await helpers.request_tx_output(self.tx_req, 0, self.coin)
        if txo.address is None:
            raise wire.DataError("Missing address.")
        script_pubkey = scripts_decred.output_script_sstxsubmissionpkh(txo.address)
        await self.approver.add_decred_sstx_submission(txo, script_pubkey)
        self.tx_info.add_output(txo, script_pubkey)
        self.write_tx_output(self.serialized_tx, txo, script_pubkey)

        # SSTX commitment
        txo = await helpers.request_tx_output(self.tx_req, 1, self.coin)
        if txo.amount != self.approver.total_in:
            raise wire.DataError("Wrong sstxcommitment amount.")
        script_pubkey = self.process_sstx_commitment_owned(txo)
        self.approver.add_change_output(txo, script_pubkey)
        self.tx_info.add_output(txo, script_pubkey)
        self.write_tx_output(self.serialized_tx, txo, script_pubkey)

        # SSTX change
        txo = await helpers.request_tx_output(self.tx_req, 2, self.coin)
        if txo.address is None:
            raise wire.DataError("Missing address.")
        script_pubkey = scripts_decred.output_script_sstxchange(txo.address)
        # Using change addresses is no longer common practice. Inputs are split
        # beforehand and should be exact. SSTX change should pay zero amount to
        # a zeroed hash.
        if txo.amount != 0:
            raise wire.DataError("Only value of 0 allowed for sstx change.")
        if script_pubkey != OUTPUT_SCRIPT_NULL_SSTXCHANGE:
            raise wire.DataError("Only zeroed addresses accepted for sstx change.")
        self.approver.add_change_output(txo, script_pubkey)
        self.tx_info.add_output(txo, script_pubkey)
        self.write_tx_output(self.serialized_tx, txo, script_pubkey)

    def write_tx_header(
        self,
        w: writers.Writer,
        tx: SignTx | PrevTx,
        witness_marker: bool,
    ) -> None:
        # The upper 16 bits of the transaction version specify the serialization
        # format and the lower 16 bits specify the version number.
        if witness_marker:
            version = tx.version | DECRED_SERIALIZE_FULL
        else:
            version = tx.version | DECRED_SERIALIZE_NO_WITNESS

        writers.write_uint32(w, version)

    def write_tx_footer(self, w: writers.Writer, tx: SignTx | PrevTx) -> None:
        assert tx.expiry is not None  # checked in sanitize_*
        writers.write_uint32(w, tx.lock_time)
        writers.write_uint32(w, tx.expiry)

    def write_tx_input_witness(
        self, w: writers.Writer, txi: TxInput, pubkey: bytes, signature: bytes
    ) -> None:
        writers.write_uint64(w, txi.amount)
        writers.write_uint32(w, 0)  # block height fraud proof
        writers.write_uint32(w, 0xFFFF_FFFF)  # block index fraud proof
        scripts_decred.write_input_script_prefixed(
            w,
            txi.script_type,
            txi.multisig,
            self.coin,
            self.get_hash_type(txi),
            pubkey,
            signature,
        )
