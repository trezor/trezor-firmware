import gc
from micropython import const

from trezor import wire
from trezor.crypto.hashlib import sha256
from trezor.messages import InputScriptType
from trezor.messages.SignTx import SignTx
from trezor.messages.TransactionType import TransactionType
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxOutputBinType import TxOutputBinType
from trezor.messages.TxOutputType import TxOutputType
from trezor.messages.TxRequest import TxRequest
from trezor.messages.TxRequestDetailsType import TxRequestDetailsType
from trezor.messages.TxRequestSerializedType import TxRequestSerializedType
from trezor.utils import HashWriter, ensure

from apps.common import coininfo, seed
from apps.common.writers import write_bitcoin_varint

from .. import addresses, common, multisig, scripts, writers
from ..common import ecdsa_hash_pubkey, ecdsa_sign
from . import helpers, progress, tx_weight
from .matchcheck import MultisigFingerprintChecker, WalletPathChecker

if False:
    from typing import Set, Tuple, Union

# Default signature hash type in Bitcoin which signs all inputs and all outputs of the transaction.
_SIGHASH_ALL = const(0x01)

# the chain id used for change
_BIP32_CHANGE_CHAIN = const(1)

# the maximum allowed change address.  this should be large enough for normal
# use and still allow to quickly brute-force the correct bip32 path
_BIP32_MAX_LAST_ELEMENT = const(1000000)

# the number of bytes to preallocate for serialized transaction chunks
_MAX_SERIALIZED_CHUNK_SIZE = const(2048)


class Bitcoin:
    async def signer(self) -> None:
        progress.init(self.tx.inputs_count, self.tx.outputs_count)

        # Add inputs to hash143 and h_confirmed and compute the sum of input amounts
        # by requesting each previous transaction and checking its output amounts.
        await self.step1_process_inputs()

        # Add outputs to hash143 and h_confirmed, confirm outputs and compute
        # sum of output amounts.
        await self.step2_confirm_outputs()

        # Check fee, confirm lock_time and total.
        await self.step3_confirm_tx()

        # Check that inputs are unchanged. Serialize inputs and sign the non-segwit ones.
        await self.step4_serialize_inputs()

        # Serialize outputs.
        await self.step5_serialize_outputs()

        # Sign segwit inputs and serialize witness data.
        await self.step6_sign_segwit_inputs()

        # Write footer and send remaining data.
        await self.step7_finish()

    def __init__(
        self, tx: SignTx, keychain: seed.Keychain, coin: coininfo.CoinInfo
    ) -> None:
        self.coin = coin
        self.tx = helpers.sanitize_sign_tx(tx, coin)
        self.keychain = keychain

        # checksum of multisig inputs, used to validate change-output
        self.multisig_fingerprint = MultisigFingerprintChecker()

        # common prefix of input paths, used to validate change-output
        self.wallet_path = WalletPathChecker()

        # set of indices of inputs which are segwit
        self.segwit = set()  # type: Set[int]

        # amounts
        self.total_in = 0  # sum of input amounts
        self.total_out = 0  # sum of output amounts
        self.change_out = 0  # change output amount
        self.weight = tx_weight.TxWeightCalculator(tx.inputs_count, tx.outputs_count)

        # transaction and signature serialization
        self.serialized_tx = writers.empty_bytearray(_MAX_SERIALIZED_CHUNK_SIZE)
        self.tx_req = TxRequest()
        self.tx_req.details = TxRequestDetailsType()
        self.tx_req.serialized = TxRequestSerializedType()
        self.tx_req.serialized.serialized_tx = self.serialized_tx

        # h_confirmed is used to make sure that the inputs and outputs streamed for
        # confirmation in Steps 1 and 2 are the same as the ones streamed for signing
        # legacy inputs in Step 4.
        self.h_confirmed = self.create_hash_writer()  # not a real tx hash

        # BIP-0143 transaction hashing
        self.init_hash143()

    def create_hash_writer(self) -> HashWriter:
        return HashWriter(sha256())

    async def step1_process_inputs(self) -> None:
        for i in range(self.tx.inputs_count):
            # STAGE_REQUEST_1_INPUT in legacy
            progress.advance()
            txi = await helpers.request_tx_input(self.tx_req, i, self.coin)
            self.weight.add_input(txi)
            if input_is_segwit(txi):
                self.segwit.add(i)
            await self.process_input(txi)

    async def step2_confirm_outputs(self) -> None:
        for i in range(self.tx.outputs_count):
            # STAGE_REQUEST_3_OUTPUT in legacy
            txo = await helpers.request_tx_output(self.tx_req, i, self.coin)
            script_pubkey = self.output_derive_script(txo)
            self.weight.add_output(script_pubkey)
            await self.confirm_output(txo, script_pubkey)

    async def step3_confirm_tx(self) -> None:
        fee = self.total_in - self.total_out

        if fee < 0:
            self.on_negative_fee()

        # fee > (coin.maxfee per byte * tx size)
        if fee > (self.coin.maxfee_kb / 1000) * (self.weight.get_total() / 4):
            await helpers.confirm_feeoverthreshold(fee, self.coin)
        if self.tx.lock_time > 0:
            await helpers.confirm_nondefault_locktime(self.tx.lock_time)
        await helpers.confirm_total(self.total_in - self.change_out, fee, self.coin)

    async def step4_serialize_inputs(self) -> None:
        self.write_tx_header(self.serialized_tx, self.tx, bool(self.segwit))
        write_bitcoin_varint(self.serialized_tx, self.tx.inputs_count)

        for i in range(self.tx.inputs_count):
            progress.advance()
            if i in self.segwit:
                await self.serialize_segwit_input(i)
            else:
                await self.sign_nonsegwit_input(i)

    async def step5_serialize_outputs(self) -> None:
        write_bitcoin_varint(self.serialized_tx, self.tx.outputs_count)
        for i in range(self.tx.outputs_count):
            progress.advance()
            await self.serialize_output(i)

    async def step6_sign_segwit_inputs(self) -> None:
        any_segwit = bool(self.segwit)
        for i in range(self.tx.inputs_count):
            progress.advance()
            if i in self.segwit:
                await self.sign_segwit_input(i)
            elif any_segwit:
                # add empty witness for non-segwit inputs
                self.serialized_tx.append(0)

    async def step7_finish(self) -> None:
        self.write_tx_footer(self.serialized_tx, self.tx)
        await helpers.request_tx_finish(self.tx_req)

    async def process_input(self, txi: TxInputType) -> None:
        self.wallet_path.add_input(txi)
        self.multisig_fingerprint.add_input(txi)
        writers.write_tx_input_check(self.h_confirmed, txi)
        self.hash143_add_input(txi)  # all inputs are included (non-segwit as well)

        if not addresses.validate_full_path(txi.address_n, self.coin, txi.script_type):
            await helpers.confirm_foreign_address(txi.address_n)

        if txi.script_type not in common.INTERNAL_INPUT_SCRIPT_TYPES:
            raise wire.DataError("Wrong input script type")

        prev_amount, script_pubkey = await self.get_prevtx_output(
            txi.prev_hash, txi.prev_index
        )

        if txi.amount is not None and prev_amount != txi.amount:
            raise wire.DataError("Invalid amount specified")

        self.total_in += prev_amount

    async def confirm_output(self, txo: TxOutputType, script_pubkey: bytes) -> None:
        if self.change_out == 0 and self.output_is_change(txo):
            # output is change and does not need confirmation
            self.change_out = txo.amount
        else:
            await helpers.confirm_output(txo, self.coin)

        self.write_tx_output(self.h_confirmed, txo, script_pubkey)
        self.hash143_add_output(txo, script_pubkey)
        self.total_out += txo.amount

    def on_negative_fee(self) -> None:
        raise wire.NotEnoughFunds("Not enough funds")

    async def serialize_segwit_input(self, i: int) -> None:
        # STAGE_REQUEST_SEGWIT_INPUT in legacy
        txi = await helpers.request_tx_input(self.tx_req, i, self.coin)

        if not input_is_segwit(txi):
            raise wire.ProcessError("Transaction has changed during signing")
        self.wallet_path.check_input(txi)
        # NOTE: No need to check the multisig fingerprint, because we won't be signing
        # the script here. Signatures are produced in STAGE_REQUEST_SEGWIT_WITNESS.

        node = self.keychain.derive(txi.address_n)
        key_sign_pub = node.public_key()
        script_sig = self.input_derive_script(txi, key_sign_pub)
        self.write_tx_input(self.serialized_tx, txi, script_sig)

    def sign_bip143_input(self, txi: TxInputType) -> Tuple[bytes, bytes]:
        if txi.amount is None:
            raise wire.DataError("Expected input with amount")

        self.wallet_path.check_input(txi)
        self.multisig_fingerprint.check_input(txi)

        node = self.keychain.derive(txi.address_n)
        public_key = node.public_key()
        hash143_hash = self.hash143_preimage_hash(
            txi, ecdsa_hash_pubkey(public_key, self.coin)
        )

        signature = ecdsa_sign(node, hash143_hash)

        return public_key, signature

    async def sign_segwit_input(self, i: int) -> None:
        # STAGE_REQUEST_SEGWIT_WITNESS in legacy
        txi = await helpers.request_tx_input(self.tx_req, i, self.coin)

        if not input_is_segwit(txi):
            raise wire.ProcessError("Transaction has changed during signing")

        public_key, signature = self.sign_bip143_input(txi)

        self.set_serialized_signature(i, signature)
        if txi.multisig:
            # find out place of our signature based on the pubkey
            signature_index = multisig.multisig_pubkey_index(txi.multisig, public_key)
            self.serialized_tx.extend(
                scripts.witness_p2wsh(
                    txi.multisig, signature, signature_index, self.get_hash_type()
                )
            )
        else:
            self.serialized_tx.extend(
                scripts.witness_p2wpkh(signature, public_key, self.get_hash_type())
            )

    async def sign_nonsegwit_input(self, i_sign: int) -> None:
        # hash of what we are signing with this input
        h_sign = self.create_hash_writer()
        # should come out the same as h_confirmed, checked before signing the digest
        h_check = self.create_hash_writer()

        self.write_tx_header(h_sign, self.tx, witness_marker=False)
        write_bitcoin_varint(h_sign, self.tx.inputs_count)

        for i in range(self.tx.inputs_count):
            # STAGE_REQUEST_4_INPUT in legacy
            txi = await helpers.request_tx_input(self.tx_req, i, self.coin)
            writers.write_tx_input_check(h_check, txi)
            if i == i_sign:
                self.wallet_path.check_input(txi)
                self.multisig_fingerprint.check_input(txi)
                # NOTE: wallet_path is checked in write_tx_input_check()
                node = self.keychain.derive(txi.address_n)
                key_sign_pub = node.public_key()
                # if multisig, do a sanity check to ensure we are signing with a key that is included in the multisig
                if txi.multisig:
                    multisig.multisig_pubkey_index(txi.multisig, key_sign_pub)

                # For the signing process the previous UTXO's scriptPubKey is included in h_sign.
                if txi.script_type == InputScriptType.SPENDMULTISIG:
                    script_pubkey = scripts.output_script_multisig(
                        multisig.multisig_get_pubkeys(txi.multisig), txi.multisig.m,
                    )
                elif txi.script_type == InputScriptType.SPENDADDRESS:
                    script_pubkey = scripts.output_script_p2pkh(
                        addresses.ecdsa_hash_pubkey(key_sign_pub, self.coin)
                    )
                else:
                    raise wire.ProcessError("Unknown transaction type")
                txi_sign = txi
            else:
                script_pubkey = bytes()
            self.write_tx_input(h_sign, txi, script_pubkey)

        write_bitcoin_varint(h_sign, self.tx.outputs_count)

        for i in range(self.tx.outputs_count):
            # STAGE_REQUEST_4_OUTPUT in legacy
            txo = await helpers.request_tx_output(self.tx_req, i, self.coin)
            script_pubkey = self.output_derive_script(txo)
            self.write_tx_output(h_check, txo, script_pubkey)
            self.write_tx_output(h_sign, txo, script_pubkey)

        writers.write_uint32(h_sign, self.tx.lock_time)
        writers.write_uint32(h_sign, self.get_hash_type())

        # check the control digests
        if self.h_confirmed.get_digest() != h_check.get_digest():
            raise wire.ProcessError("Transaction has changed during signing")

        # compute the signature from the tx digest
        signature = ecdsa_sign(
            node, writers.get_tx_hash(h_sign, double=self.coin.sign_hash_double)
        )

        # serialize input with correct signature
        gc.collect()
        script_sig = self.input_derive_script(txi_sign, key_sign_pub, signature)
        self.write_tx_input(self.serialized_tx, txi_sign, script_sig)
        self.set_serialized_signature(i_sign, signature)

    async def serialize_output(self, i: int) -> None:
        # STAGE_REQUEST_5_OUTPUT in legacy
        txo = await helpers.request_tx_output(self.tx_req, i, self.coin)
        script_pubkey = self.output_derive_script(txo)
        self.write_tx_output(self.serialized_tx, txo, script_pubkey)

    async def get_prevtx_output(
        self, prev_hash: bytes, prev_index: int
    ) -> Tuple[int, bytes]:
        amount_out = 0  # output amount

        # STAGE_REQUEST_2_PREV_META in legacy
        tx = await helpers.request_tx_meta(self.tx_req, self.coin, prev_hash)

        if tx.outputs_cnt <= prev_index:
            raise wire.ProcessError("Not enough outputs in previous transaction.")

        txh = self.create_hash_writer()

        # witnesses are not included in txid hash
        self.write_tx_header(txh, tx, witness_marker=False)
        write_bitcoin_varint(txh, tx.inputs_cnt)

        for i in range(tx.inputs_cnt):
            # STAGE_REQUEST_2_PREV_INPUT in legacy
            txi = await helpers.request_tx_input(self.tx_req, i, self.coin, prev_hash)
            self.write_tx_input(txh, txi, txi.script_sig)

        write_bitcoin_varint(txh, tx.outputs_cnt)

        for i in range(tx.outputs_cnt):
            # STAGE_REQUEST_2_PREV_OUTPUT in legacy
            txo_bin = await helpers.request_tx_output(
                self.tx_req, i, self.coin, prev_hash
            )
            self.write_tx_output(txh, txo_bin, txo_bin.script_pubkey)
            if i == prev_index:
                amount_out = txo_bin.amount
                script_pubkey = txo_bin.script_pubkey
                self.check_prevtx_output(txo_bin)

        await self.write_prev_tx_footer(txh, tx, prev_hash)

        if (
            writers.get_tx_hash(txh, double=self.coin.sign_hash_double, reverse=True)
            != prev_hash
        ):
            raise wire.ProcessError("Encountered invalid prev_hash")

        return amount_out, script_pubkey

    def check_prevtx_output(self, txo_bin: TxOutputBinType) -> None:
        # Validations to perform on the UTXO when checking the previous transaction output amount.
        pass

    # Tx Helpers
    # ===

    def get_hash_type(self) -> int:
        return _SIGHASH_ALL

    def write_tx_input(
        self, w: writers.Writer, txi: TxInputType, script: bytes
    ) -> None:
        writers.write_tx_input(w, txi, script)

    def write_tx_output(
        self,
        w: writers.Writer,
        txo: Union[TxOutputType, TxOutputBinType],
        script_pubkey: bytes,
    ) -> None:
        writers.write_tx_output(w, txo, script_pubkey)

    def write_tx_header(
        self,
        w: writers.Writer,
        tx: Union[SignTx, TransactionType],
        witness_marker: bool,
    ) -> None:
        writers.write_uint32(w, tx.version)  # nVersion
        if witness_marker:
            write_bitcoin_varint(w, 0x00)  # segwit witness marker
            write_bitcoin_varint(w, 0x01)  # segwit witness flag

    def write_tx_footer(
        self, w: writers.Writer, tx: Union[SignTx, TransactionType]
    ) -> None:
        writers.write_uint32(w, tx.lock_time)

    async def write_prev_tx_footer(
        self, w: writers.Writer, tx: TransactionType, prev_hash: bytes
    ) -> None:
        self.write_tx_footer(w, tx)

    def set_serialized_signature(self, index: int, signature: bytes) -> None:
        # Only one signature per TxRequest can be serialized.
        ensure(self.tx_req.serialized.signature is None)

        self.tx_req.serialized.signature_index = index
        self.tx_req.serialized.signature = signature

    # Tx Outputs
    # ===

    def output_derive_script(self, txo: TxOutputType) -> bytes:
        if txo.script_type == OutputScriptType.PAYTOOPRETURN:
            return scripts.output_script_paytoopreturn(txo.op_return_data)

        if txo.address_n:
            # change output
            try:
                input_script_type = common.CHANGE_OUTPUT_TO_INPUT_SCRIPT_TYPES[
                    txo.script_type
                ]
            except KeyError:
                raise wire.DataError("Invalid script type")
            node = self.keychain.derive(txo.address_n)
            txo.address = addresses.get_address(
                input_script_type, self.coin, node, txo.multisig
            )

        return scripts.output_derive_script(txo.address, self.coin)

    def output_is_change(self, txo: TxOutputType) -> bool:
        if txo.script_type not in common.CHANGE_OUTPUT_SCRIPT_TYPES:
            return False
        if txo.multisig and not self.multisig_fingerprint.output_matches(txo):
            return False
        return (
            self.wallet_path.output_matches(txo)
            and txo.address_n[-2] <= _BIP32_CHANGE_CHAIN
            and txo.address_n[-1] <= _BIP32_MAX_LAST_ELEMENT
            and txo.amount > 0
        )

    # Tx Inputs
    # ===

    def input_derive_script(
        self, txi: TxInputType, pubkey: bytes, signature: bytes = None
    ) -> bytes:
        return scripts.input_derive_script(
            txi, self.coin, self.get_hash_type(), pubkey, signature
        )

    # BIP-0143
    # ===

    def init_hash143(self) -> None:
        self.h_prevouts = HashWriter(sha256())
        self.h_sequence = HashWriter(sha256())
        self.h_outputs = HashWriter(sha256())

    def hash143_add_input(self, txi: TxInputType) -> None:
        writers.write_bytes_reversed(
            self.h_prevouts, txi.prev_hash, writers.TX_HASH_SIZE
        )
        writers.write_uint32(self.h_prevouts, txi.prev_index)
        writers.write_uint32(self.h_sequence, txi.sequence)

    def hash143_add_output(self, txo: TxOutputType, script_pubkey) -> None:
        writers.write_tx_output(self.h_outputs, txo, script_pubkey)

    def hash143_preimage_hash(self, txi: TxInputType, pubkeyhash: bytes) -> bytes:
        h_preimage = HashWriter(sha256())

        # nVersion
        writers.write_uint32(h_preimage, self.tx.version)

        # hashPrevouts
        prevouts_hash = writers.get_tx_hash(
            self.h_prevouts, double=self.coin.sign_hash_double
        )
        writers.write_bytes_fixed(h_preimage, prevouts_hash, writers.TX_HASH_SIZE)

        # hashSequence
        sequence_hash = writers.get_tx_hash(
            self.h_sequence, double=self.coin.sign_hash_double
        )
        writers.write_bytes_fixed(h_preimage, sequence_hash, writers.TX_HASH_SIZE)

        # outpoint
        writers.write_bytes_reversed(h_preimage, txi.prev_hash, writers.TX_HASH_SIZE)
        writers.write_uint32(h_preimage, txi.prev_index)

        # scriptCode
        script_code = scripts.bip143_derive_script_code(txi, pubkeyhash)
        writers.write_bytes_prefixed(h_preimage, script_code)

        # amount
        writers.write_uint64(h_preimage, txi.amount)

        # nSequence
        writers.write_uint32(h_preimage, txi.sequence)

        # hashOutputs
        outputs_hash = writers.get_tx_hash(
            self.h_outputs, double=self.coin.sign_hash_double
        )
        writers.write_bytes_fixed(h_preimage, outputs_hash, writers.TX_HASH_SIZE)

        # nLockTime
        writers.write_uint32(h_preimage, self.tx.lock_time)

        # nHashType
        writers.write_uint32(h_preimage, self.get_hash_type())

        return writers.get_tx_hash(h_preimage, double=self.coin.sign_hash_double)


def input_is_segwit(txi: TxInputType) -> bool:
    return txi.script_type in common.SEGWIT_INPUT_SCRIPT_TYPES


def input_is_nonsegwit(txi: TxInputType) -> bool:
    return txi.script_type in common.NONSEGWIT_INPUT_SCRIPT_TYPES
