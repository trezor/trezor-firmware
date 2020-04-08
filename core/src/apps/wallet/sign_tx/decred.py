import gc
from micropython import const

from trezor.crypto.hashlib import blake256
from trezor.messages import FailureType, InputScriptType
from trezor.messages.SignTx import SignTx
from trezor.messages.TransactionType import TransactionType
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxOutputBinType import TxOutputBinType
from trezor.messages.TxOutputType import TxOutputType
from trezor.messages.TxRequestSerializedType import TxRequestSerializedType
from trezor.utils import HashWriter, ensure

from apps.common import coininfo, seed
from apps.wallet.sign_tx import addresses, helpers, multisig, progress, scripts, writers
from apps.wallet.sign_tx.segwit_bip143 import Bip143
from apps.wallet.sign_tx.signing import Bitcoin, SigningError, ecdsa_sign

DECRED_SERIALIZE_FULL = const(0 << 16)
DECRED_SERIALIZE_NO_WITNESS = const(1 << 16)
DECRED_SERIALIZE_WITNESS_SIGNING = const(3 << 16)

DECRED_SIGHASHALL = const(1)

if False:
    from typing import Union


class DecredPrefixHasher(Bip143):
    """
    While Decred does not have the exact same implementation as bip143/zip143,
    the semantics for using the prefix hash of transactions are close enough
    that a pseudo-bip143 class can be used.
    """

    def __init__(self, tx: SignTx):
        self.h_prefix = HashWriter(blake256())
        writers.write_uint32(self.h_prefix, tx.version | DECRED_SERIALIZE_NO_WITNESS)
        writers.write_varint(self.h_prefix, tx.inputs_count)

    def add_prevouts(self, txi: TxInputType) -> None:
        writers.write_tx_input_decred(self.h_prefix, txi)

    def add_sequence(self, txi: TxInputType) -> None:
        pass

    def add_output_count(self, tx: SignTx) -> None:
        writers.write_varint(self.h_prefix, tx.outputs_count)

    def add_output(self, txo_bin: TxOutputBinType) -> None:
        writers.write_tx_output(self.h_prefix, txo_bin)

    def add_locktime_expiry(self, tx: SignTx) -> None:
        writers.write_uint32(self.h_prefix, tx.lock_time)
        writers.write_uint32(self.h_prefix, tx.expiry)

    def get_prefix_hash(self) -> bytes:
        return self.h_prefix.get_digest()


class Decred(Bitcoin):
    def initialize(
        self, tx: SignTx, keychain: seed.Keychain, coin: coininfo.CoinInfo
    ) -> None:
        ensure(coin.decred)
        super().initialize(tx, keychain, coin)

        # This is required because the last serialized output obtained in
        # phase 1 will only be sent to the client in phase 2
        self.last_output_bytes = None  # type: bytearray

    def init_hash143(self) -> None:
        self.hash143 = DecredPrefixHasher(self.tx)  # pseudo BIP-0143 prefix hashing

    def create_hash_writer(self) -> HashWriter:
        return HashWriter(blake256())

    async def phase1(self) -> None:
        await super().phase1()
        self.hash143.add_locktime_expiry(self.tx)

    async def phase1_process_input(self, i: int, txi: TxInputType) -> None:
        await super().phase1_process_input(i, txi)
        w_txi = writers.empty_bytearray(8 if i == 0 else 0 + 9 + len(txi.prev_hash))
        if i == 0:  # serializing first input => prepend headers
            self.write_sign_tx_header(w_txi, False)
        self.write_tx_input(w_txi, txi)
        self.tx_req.serialized = TxRequestSerializedType(None, None, w_txi)

    async def phase1_confirm_output(
        self, i: int, txo: TxOutputType, txo_bin: TxOutputBinType
    ) -> None:
        if txo.decred_script_version is not None and txo.decred_script_version != 0:
            raise SigningError(
                FailureType.ActionCancelled,
                "Cannot send to output with script version != 0",
            )
        txo_bin.decred_script_version = txo.decred_script_version

        w_txo_bin = writers.empty_bytearray(4 + 8 + 2 + 4 + len(txo_bin.script_pubkey))
        if i == 0:  # serializing first output => prepend outputs count
            writers.write_varint(w_txo_bin, self.tx.outputs_count)
            self.hash143.add_output_count(self.tx)

        writers.write_tx_output(w_txo_bin, txo_bin)
        self.tx_req.serialized = TxRequestSerializedType(serialized_tx=w_txo_bin)
        self.last_output_bytes = w_txo_bin

        await super().phase1_confirm_output(i, txo, txo_bin)

    async def phase2(self) -> None:
        self.tx_req.serialized = None

        prefix_hash = self.hash143.get_prefix_hash()

        for i_sign in range(self.tx.inputs_count):
            progress.advance()

            txi_sign = await helpers.request_tx_input(self.tx_req, i_sign, self.coin)

            self.input_check_wallet_path(txi_sign)
            self.input_check_multisig_fingerprint(txi_sign)

            key_sign = self.keychain.derive(txi_sign.address_n, self.coin.curve_name)
            key_sign_pub = key_sign.public_key()

            if txi_sign.script_type == InputScriptType.SPENDMULTISIG:
                prev_pkscript = scripts.output_script_multisig(
                    multisig.multisig_get_pubkeys(txi_sign.multisig),
                    txi_sign.multisig.m,
                )
            elif txi_sign.script_type == InputScriptType.SPENDADDRESS:
                prev_pkscript = scripts.output_script_p2pkh(
                    addresses.ecdsa_hash_pubkey(key_sign_pub, self.coin)
                )
            else:
                raise SigningError("Unsupported input script type")

            h_witness = self.create_hash_writer()
            writers.write_uint32(
                h_witness, self.tx.version | DECRED_SERIALIZE_WITNESS_SIGNING
            )
            writers.write_varint(h_witness, self.tx.inputs_count)

            for ii in range(self.tx.inputs_count):
                if ii == i_sign:
                    writers.write_bytes_prefixed(h_witness, prev_pkscript)
                else:
                    writers.write_varint(h_witness, 0)

            witness_hash = writers.get_tx_hash(
                h_witness, double=self.coin.sign_hash_double, reverse=False
            )

            h_sign = self.create_hash_writer()
            writers.write_uint32(h_sign, DECRED_SIGHASHALL)
            writers.write_bytes_fixed(h_sign, prefix_hash, writers.TX_HASH_SIZE)
            writers.write_bytes_fixed(h_sign, witness_hash, writers.TX_HASH_SIZE)

            sig_hash = writers.get_tx_hash(h_sign, double=self.coin.sign_hash_double)
            signature = ecdsa_sign(key_sign, sig_hash)

            # serialize input with correct signature
            gc.collect()
            txi_sign.script_sig = self.input_derive_script(
                txi_sign, key_sign_pub, signature
            )
            w_txi_sign = writers.empty_bytearray(
                8 + 4 + len(self.last_output_bytes)
                if i_sign == 0
                else 0 + 16 + 4 + len(txi_sign.script_sig)
            )

            if i_sign == 0:
                writers.write_bytes_unchecked(w_txi_sign, self.last_output_bytes)
                writers.write_uint32(w_txi_sign, self.tx.lock_time)
                writers.write_uint32(w_txi_sign, self.tx.expiry)
                writers.write_varint(w_txi_sign, self.tx.inputs_count)

            writers.write_tx_input_decred_witness(w_txi_sign, txi_sign)
            self.tx_req.serialized = TxRequestSerializedType(
                i_sign, signature, w_txi_sign
            )

        await helpers.request_tx_finish(self.tx_req)

    def check_prevtx_output(self, txo_bin: TxOutputBinType) -> None:
        if (
            txo_bin.decred_script_version is not None
            and txo_bin.decred_script_version != 0
        ):
            raise SigningError(
                FailureType.ProcessError,
                "Cannot use utxo that has script_version != 0",
            )

    def write_tx_input(self, w: writers.Writer, i: TxInputType) -> None:
        writers.write_tx_input_decred(w, i)

    def write_sign_tx_header(self, w: writers.Writer, has_segwit: bool) -> None:
        writers.write_uint32(w, self.tx.version)  # nVersion
        writers.write_varint(w, self.tx.inputs_count)

    def write_tx_header(
        self, w: writers.Writer, tx: Union[SignTx, TransactionType], has_segwit: bool
    ) -> None:
        writers.write_uint32(w, tx.version | DECRED_SERIALIZE_NO_WITNESS)

    async def write_prev_tx_footer(
        self, w: writers.Writer, tx: TransactionType, prev_hash: bytes
    ) -> None:
        writers.write_uint32(w, tx.lock_time)
        writers.write_uint32(w, tx.expiry)
