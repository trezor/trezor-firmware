from micropython import const

from trezor import wire
from trezor.crypto.hashlib import blake256
from trezor.messages import InputScriptType
from trezor.messages.SignTx import SignTx
from trezor.messages.TransactionType import TransactionType
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxOutputBinType import TxOutputBinType
from trezor.messages.TxOutputType import TxOutputType
from trezor.utils import HashWriter, ensure

from apps.common import coininfo, seed
from apps.common.writers import write_bitcoin_varint

from .. import multisig, scripts, writers
from ..common import ecdsa_hash_pubkey, ecdsa_sign
from . import approvers, helpers, progress
from .bitcoin import Bitcoin

DECRED_SERIALIZE_FULL = const(0 << 16)
DECRED_SERIALIZE_NO_WITNESS = const(1 << 16)
DECRED_SERIALIZE_WITNESS_SIGNING = const(3 << 16)
DECRED_SCRIPT_VERSION = const(0)

DECRED_SIGHASH_ALL = const(1)

if False:
    from typing import Union


class Decred(Bitcoin):
    def __init__(
        self,
        tx: SignTx,
        keychain: seed.Keychain,
        coin: coininfo.CoinInfo,
        approver: approvers.Approver,
    ) -> None:
        ensure(coin.decred)
        super().__init__(tx, keychain, coin, approver)

        self.write_tx_header(self.serialized_tx, self.tx, witness_marker=True)
        write_bitcoin_varint(self.serialized_tx, self.tx.inputs_count)

    def init_hash143(self) -> None:
        self.h_prefix = self.create_hash_writer()
        writers.write_uint32(
            self.h_prefix, self.tx.version | DECRED_SERIALIZE_NO_WITNESS
        )
        write_bitcoin_varint(self.h_prefix, self.tx.inputs_count)

    def create_hash_writer(self) -> HashWriter:
        return HashWriter(blake256())

    async def step2_approve_outputs(self) -> None:
        write_bitcoin_varint(self.serialized_tx, self.tx.outputs_count)
        write_bitcoin_varint(self.h_prefix, self.tx.outputs_count)
        await super().step2_approve_outputs()
        self.write_tx_footer(self.serialized_tx, self.tx)
        self.write_tx_footer(self.h_prefix, self.tx)

    async def process_internal_input(self, txi: TxInputType) -> None:
        await super().process_internal_input(txi)

        # Decred serializes inputs early.
        self.write_tx_input(self.serialized_tx, txi, bytes())

    async def process_external_input(self, txi: TxInputType) -> None:
        raise wire.DataError("External inputs not supported")

    async def approve_output(self, txo: TxOutputType, script_pubkey: bytes) -> None:
        await super().approve_output(txo, script_pubkey)
        self.write_tx_output(self.serialized_tx, txo, script_pubkey)

    async def step4_serialize_inputs(self) -> None:
        write_bitcoin_varint(self.serialized_tx, self.tx.inputs_count)

        prefix_hash = self.h_prefix.get_digest()

        for i_sign in range(self.tx.inputs_count):
            progress.advance()

            txi_sign = await helpers.request_tx_input(self.tx_req, i_sign, self.coin)

            self.wallet_path.check_input(txi_sign)
            self.multisig_fingerprint.check_input(txi_sign)

            key_sign = self.keychain.derive(txi_sign.address_n)
            key_sign_pub = key_sign.public_key()

            if txi_sign.script_type == InputScriptType.SPENDMULTISIG:
                prev_pkscript = scripts.output_script_multisig(
                    multisig.multisig_get_pubkeys(txi_sign.multisig),
                    txi_sign.multisig.m,
                )
            elif txi_sign.script_type == InputScriptType.SPENDADDRESS:
                prev_pkscript = scripts.output_script_p2pkh(
                    ecdsa_hash_pubkey(key_sign_pub, self.coin)
                )
            else:
                raise wire.DataError("Unsupported input script type")

            h_witness = self.create_hash_writer()
            writers.write_uint32(
                h_witness, self.tx.version | DECRED_SERIALIZE_WITNESS_SIGNING
            )
            write_bitcoin_varint(h_witness, self.tx.inputs_count)

            for ii in range(self.tx.inputs_count):
                if ii == i_sign:
                    writers.write_bytes_prefixed(h_witness, prev_pkscript)
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
            script_sig = self.input_derive_script(txi_sign, key_sign_pub, signature)
            self.write_tx_input_witness(self.serialized_tx, txi_sign, script_sig)
            self.set_serialized_signature(i_sign, signature)

    async def step5_serialize_outputs(self) -> None:
        pass

    async def step6_sign_segwit_inputs(self) -> None:
        pass

    async def step7_finish(self) -> None:
        await helpers.request_tx_finish(self.tx_req)

    def check_prevtx_output(self, txo_bin: TxOutputBinType) -> None:
        if txo_bin.decred_script_version != 0:
            raise wire.ProcessError("Cannot use utxo that has script_version != 0")

    def hash143_add_input(self, txi: TxInputType) -> None:
        self.write_tx_input(self.h_prefix, txi, bytes())

    def hash143_add_output(self, txo: TxOutputType, script_pubkey: bytes) -> None:
        self.write_tx_output(self.h_prefix, txo, script_pubkey)

    def write_tx_input(
        self, w: writers.Writer, txi: TxInputType, script: bytes
    ) -> None:
        writers.write_bytes_reversed(w, txi.prev_hash, writers.TX_HASH_SIZE)
        writers.write_uint32(w, txi.prev_index or 0)
        writers.write_uint8(w, txi.decred_tree or 0)
        writers.write_uint32(w, txi.sequence)

    def write_tx_output(
        self,
        w: writers.Writer,
        txo: Union[TxOutputType, TxOutputBinType],
        script_pubkey: bytes,
    ) -> None:
        writers.write_uint64(w, txo.amount)
        if isinstance(txo, TxOutputBinType):
            writers.write_uint16(w, txo.decred_script_version)
        else:
            writers.write_uint16(w, DECRED_SCRIPT_VERSION)
        writers.write_bytes_prefixed(w, script_pubkey)

    def write_tx_header(
        self,
        w: writers.Writer,
        tx: Union[SignTx, TransactionType],
        witness_marker: bool,
    ) -> None:
        # The upper 16 bits of the transaction version specify the serialization
        # format and the lower 16 bits specify the version number.
        if witness_marker:
            version = tx.version | DECRED_SERIALIZE_FULL
        else:
            version = tx.version | DECRED_SERIALIZE_NO_WITNESS

        writers.write_uint32(w, version)

    def write_tx_footer(
        self, w: writers.Writer, tx: Union[SignTx, TransactionType]
    ) -> None:
        writers.write_uint32(w, tx.lock_time)
        writers.write_uint32(w, tx.expiry)

    def write_tx_input_witness(
        self, w: writers.Writer, i: TxInputType, script_sig: bytes
    ) -> None:
        writers.write_uint64(w, i.amount)
        writers.write_uint32(w, 0)  # block height fraud proof
        writers.write_uint32(w, 0xFFFFFFFF)  # block index fraud proof
        writers.write_bytes_prefixed(w, script_sig)
