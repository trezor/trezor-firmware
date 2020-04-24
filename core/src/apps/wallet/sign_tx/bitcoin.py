import gc
from micropython import const

from trezor.crypto.hashlib import sha256
from trezor.messages import FailureType, InputScriptType
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
from apps.wallet.sign_tx import (
    addresses,
    helpers,
    multisig,
    progress,
    scripts,
    segwit_bip143,
    tx_weight,
    writers,
)
from apps.wallet.sign_tx.common import SigningError, ecdsa_sign
from apps.wallet.sign_tx.matchcheck import MultisigFingerprintChecker, WalletPathChecker

if False:
    from typing import Set, Tuple, Union

# Default signature hash type in Bitcoin, which signs the entire transaction except scripts.
_SIGHASH_ALL = const(0x01)

# the chain id used for change
_BIP32_CHANGE_CHAIN = const(1)

# the maximum allowed change address.  this should be large enough for normal
# use and still allow to quickly brute-force the correct bip32 path
_BIP32_MAX_LAST_ELEMENT = const(1000000)

# the number of bytes to preallocate for serialized transaction chunks
_MAX_SERIALIZED_CHUNK_SIZE = const(2048)


# Transaction signing
# ===
# see https://github.com/trezor/trezor-mcu/blob/master/firmware/signing.c#L84
# for pseudo code overview
# ===


class Bitcoin:
    async def signer(self) -> None:
        progress.init(self.tx.inputs_count, self.tx.outputs_count)

        # Add inputs to hash143 and h_confirmed and compute the sum of input amounts.
        await self.step1_process_inputs()

        # Add outputs to hash143 and h_confirmed, check previous transaction output
        # amounts, confirm outputs and compute sum of output amounts.
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
        self.bip143_in = 0  # sum of segwit input amounts
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
        self.hash143 = self.create_hash143()

    def create_hash143(self) -> segwit_bip143.Bip143:
        return segwit_bip143.Bip143()

    def create_hash_writer(self) -> HashWriter:
        return HashWriter(sha256())

    async def step1_process_inputs(self) -> None:
        for i in range(self.tx.inputs_count):
            # STAGE_REQUEST_1_INPUT
            progress.advance()
            txi = await helpers.request_tx_input(self.tx_req, i, self.coin)
            self.weight.add_input(txi)
            await self.process_input(i, txi)

    async def step2_confirm_outputs(self) -> None:
        txo_bin = TxOutputBinType()
        for i in range(self.tx.outputs_count):
            # STAGE_REQUEST_3_OUTPUT
            txo = await helpers.request_tx_output(self.tx_req, i, self.coin)
            txo_bin.amount = txo.amount
            txo_bin.script_pubkey = self.output_derive_script(txo)
            self.weight.add_output(txo_bin.script_pubkey)
            await self.confirm_output(i, txo, txo_bin)

    async def step3_confirm_tx(self) -> None:
        fee = self.total_in - self.total_out

        if fee < 0:
            self.on_negative_fee()

        # fee > (coin.maxfee per byte * tx size)
        if fee > (self.coin.maxfee_kb / 1000) * (self.weight.get_total() / 4):
            if not await helpers.confirm_feeoverthreshold(fee, self.coin):
                raise SigningError(FailureType.ActionCancelled, "Signing cancelled")

        if self.tx.lock_time > 0:
            if not await helpers.confirm_nondefault_locktime(self.tx.lock_time):
                raise SigningError(FailureType.ActionCancelled, "Locktime cancelled")

        if not await helpers.confirm_total(
            self.total_in - self.change_out, fee, self.coin
        ):
            raise SigningError(FailureType.ActionCancelled, "Total cancelled")

    async def step4_serialize_inputs(self) -> None:
        self.write_tx_header(self.serialized_tx, self.tx, bool(self.segwit))
        writers.write_varint(self.serialized_tx, self.tx.inputs_count)

        for i in range(self.tx.inputs_count):
            progress.advance()
            if i in self.segwit:
                await self.serialize_segwit_input(i)
            else:
                await self.sign_nonsegwit_input(i)

    async def step5_serialize_outputs(self) -> None:
        writers.write_varint(self.serialized_tx, self.tx.outputs_count)
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

    async def process_input(self, i: int, txi: TxInputType) -> None:
        self.wallet_path.add_input(txi)
        self.multisig_fingerprint.add_input(txi)
        writers.write_tx_input_check(self.h_confirmed, txi)
        self.hash143.add_input(txi)  # all inputs are included (non-segwit as well)

        if not addresses.validate_full_path(txi.address_n, self.coin, txi.script_type):
            await helpers.confirm_foreign_address(txi.address_n)

        if input_is_segwit(txi):
            self.segwit.add(i)
            await self.process_segwit_input(i, txi)
        elif input_is_nonsegwit(txi):
            await self.process_nonsegwit_input(i, txi)
        else:
            raise SigningError(FailureType.DataError, "Wrong input script type")

    async def process_segwit_input(self, i: int, txi: TxInputType) -> None:
        await self.process_bip143_input(i, txi)

    async def process_nonsegwit_input(self, i: int, txi: TxInputType) -> None:
        self.total_in += await self.get_prevtx_output_value(
            txi.prev_hash, txi.prev_index
        )

    async def process_bip143_input(self, i: int, txi: TxInputType) -> None:
        if not txi.amount:
            raise SigningError(FailureType.DataError, "Expected input with amount")
        self.bip143_in += txi.amount
        self.total_in += txi.amount

    async def confirm_output(
        self, i: int, txo: TxOutputType, txo_bin: TxOutputBinType
    ) -> None:
        if self.change_out == 0 and self.output_is_change(txo):
            # output is change and does not need confirmation
            self.change_out = txo.amount
        elif not await helpers.confirm_output(txo, self.coin):
            raise SigningError(FailureType.ActionCancelled, "Output cancelled")

        writers.write_tx_output(self.h_confirmed, txo_bin)
        self.hash143.add_output(txo_bin)
        self.total_out += txo_bin.amount

    def on_negative_fee(self) -> None:
        raise SigningError(FailureType.NotEnoughFunds, "Not enough funds")

    async def serialize_segwit_input(self, i: int) -> None:
        # STAGE_REQUEST_SEGWIT_INPUT
        txi = await helpers.request_tx_input(self.tx_req, i, self.coin)

        if not input_is_segwit(txi):
            raise SigningError(
                FailureType.ProcessError, "Transaction has changed during signing"
            )
        self.wallet_path.check_input(txi)
        # NOTE: No need to check the multisig fingerprint, because we won't be signing
        # the script here. Signatures are produced in STAGE_REQUEST_SEGWIT_WITNESS.

        node = self.keychain.derive(txi.address_n, self.coin.curve_name)
        key_sign_pub = node.public_key()
        txi.script_sig = self.input_derive_script(txi, key_sign_pub)

        self.write_tx_input(self.serialized_tx, txi)

    def sign_bip143_input(self, txi: TxInputType) -> Tuple[bytes, bytes]:
        self.wallet_path.check_input(txi)
        self.multisig_fingerprint.check_input(txi)

        if txi.amount > self.bip143_in:
            raise SigningError(
                FailureType.ProcessError, "Transaction has changed during signing"
            )
        self.bip143_in -= txi.amount

        node = self.keychain.derive(txi.address_n, self.coin.curve_name)
        public_key = node.public_key()
        hash143_hash = self.hash143.preimage_hash(
            self.coin,
            self.tx,
            txi,
            addresses.ecdsa_hash_pubkey(public_key, self.coin),
            self.get_hash_type(),
        )

        signature = ecdsa_sign(node, hash143_hash)

        return public_key, signature

    async def sign_segwit_input(self, i: int) -> None:
        # STAGE_REQUEST_SEGWIT_WITNESS
        txi = await helpers.request_tx_input(self.tx_req, i, self.coin)

        if not input_is_segwit(txi):
            raise SigningError(
                FailureType.ProcessError, "Transaction has changed during signing"
            )

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

        self.write_tx_header(h_sign, self.tx, has_segwit=False)
        writers.write_varint(h_sign, self.tx.inputs_count)

        for i in range(self.tx.inputs_count):
            # STAGE_REQUEST_4_INPUT
            txi = await helpers.request_tx_input(self.tx_req, i, self.coin)
            writers.write_tx_input_check(h_check, txi)
            if i == i_sign:
                txi_sign = txi
                self.wallet_path.check_input(txi_sign)
                self.multisig_fingerprint.check_input(txi_sign)
                # NOTE: wallet_path is checked in write_tx_input_check()
                node = self.keychain.derive(txi.address_n, self.coin.curve_name)
                key_sign_pub = node.public_key()
                # for the signing process the script_sig is equal
                # to the previous tx's scriptPubKey (P2PKH) or a redeem script (P2SH)
                if txi_sign.script_type == InputScriptType.SPENDMULTISIG:
                    txi_sign.script_sig = scripts.output_script_multisig(
                        multisig.multisig_get_pubkeys(txi_sign.multisig),
                        txi_sign.multisig.m,
                    )
                elif txi_sign.script_type == InputScriptType.SPENDADDRESS:
                    txi_sign.script_sig = scripts.output_script_p2pkh(
                        addresses.ecdsa_hash_pubkey(key_sign_pub, self.coin)
                    )
                else:
                    raise SigningError(
                        FailureType.ProcessError, "Unknown transaction type"
                    )
            else:
                txi.script_sig = bytes()
            self.write_tx_input(h_sign, txi)

        writers.write_varint(h_sign, self.tx.outputs_count)

        txo_bin = TxOutputBinType()
        for i in range(self.tx.outputs_count):
            # STAGE_REQUEST_4_OUTPUT
            txo = await helpers.request_tx_output(self.tx_req, i, self.coin)
            txo_bin.amount = txo.amount
            txo_bin.script_pubkey = self.output_derive_script(txo)
            writers.write_tx_output(h_check, txo_bin)
            writers.write_tx_output(h_sign, txo_bin)

        writers.write_uint32(h_sign, self.tx.lock_time)
        writers.write_uint32(h_sign, self.get_hash_type())

        # check the control digests
        if self.h_confirmed.get_digest() != h_check.get_digest():
            raise SigningError(
                FailureType.ProcessError, "Transaction has changed during signing"
            )

        # if multisig, do a sanity check to ensure we are signing with a key that is included in the multisig
        if txi_sign.multisig:
            multisig.multisig_pubkey_index(txi_sign.multisig, key_sign_pub)

        # compute the signature from the tx digest
        signature = ecdsa_sign(
            node, writers.get_tx_hash(h_sign, double=self.coin.sign_hash_double)
        )

        # serialize input with correct signature
        gc.collect()
        txi_sign.script_sig = self.input_derive_script(
            txi_sign, key_sign_pub, signature
        )
        self.write_tx_input(self.serialized_tx, txi_sign)
        self.set_serialized_signature(i_sign, signature)

    async def serialize_output(self, i: int) -> None:
        # STAGE_REQUEST_5_OUTPUT
        txo = await helpers.request_tx_output(self.tx_req, i, self.coin)
        txo_bin = TxOutputBinType()
        txo_bin.amount = txo.amount
        txo_bin.script_pubkey = self.output_derive_script(txo)
        writers.write_tx_output(self.serialized_tx, txo_bin)

    async def get_prevtx_output_value(self, prev_hash: bytes, prev_index: int) -> int:
        amount_out = 0  # output amount

        # STAGE_REQUEST_2_PREV_META
        tx = await helpers.request_tx_meta(self.tx_req, self.coin, prev_hash)

        if tx.outputs_cnt <= prev_index:
            raise SigningError(
                FailureType.ProcessError, "Not enough outputs in previous transaction."
            )

        txh = self.create_hash_writer()

        # TODO set has_segwit correctly
        self.write_tx_header(txh, tx, has_segwit=False)
        writers.write_varint(txh, tx.inputs_cnt)

        for i in range(tx.inputs_cnt):
            # STAGE_REQUEST_2_PREV_INPUT
            txi = await helpers.request_tx_input(self.tx_req, i, self.coin, prev_hash)
            self.write_tx_input(txh, txi)

        writers.write_varint(txh, tx.outputs_cnt)

        for i in range(tx.outputs_cnt):
            # STAGE_REQUEST_2_PREV_OUTPUT
            txo_bin = await helpers.request_tx_output(
                self.tx_req, i, self.coin, prev_hash
            )
            writers.write_tx_output(txh, txo_bin)
            if i == prev_index:
                amount_out = txo_bin.amount
                self.check_prevtx_output(txo_bin)

        await self.write_prev_tx_footer(txh, tx, prev_hash)

        if (
            writers.get_tx_hash(txh, double=self.coin.sign_hash_double, reverse=True)
            != prev_hash
        ):
            raise SigningError(
                FailureType.ProcessError, "Encountered invalid prev_hash"
            )

        return amount_out

    def check_prevtx_output(self, txo_bin: TxOutputBinType) -> None:
        # Validations to perform on the UTXO when checking the previous transaction output amount.
        pass

    # TX Helpers
    # ===

    def get_hash_type(self) -> int:
        return _SIGHASH_ALL

    def write_tx_input(self, w: writers.Writer, txi: TxInputType) -> None:
        writers.write_tx_input(w, txi)

    def write_tx_header(
        self, w: writers.Writer, tx: Union[SignTx, TransactionType], has_segwit: bool
    ) -> None:
        writers.write_uint32(w, tx.version)  # nVersion
        if has_segwit:
            writers.write_varint(w, 0x00)  # segwit witness marker
            writers.write_varint(w, 0x01)  # segwit witness flag

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

    # TX Outputs
    # ===

    def output_derive_script(self, txo: TxOutputType) -> bytes:
        if txo.address_n:
            # change output
            try:
                input_script_type = helpers.CHANGE_OUTPUT_TO_INPUT_SCRIPT_TYPES[
                    txo.script_type
                ]
            except KeyError:
                raise SigningError(FailureType.DataError, "Invalid script type")
            node = self.keychain.derive(txo.address_n, self.coin.curve_name)
            txo.address = addresses.get_address(
                input_script_type, self.coin, node, txo.multisig
            )

        return scripts.output_derive_script(txo, self.coin)

    def output_is_change(self, txo: TxOutputType) -> bool:
        if txo.script_type not in helpers.CHANGE_OUTPUT_SCRIPT_TYPES:
            return False
        if txo.multisig and not self.multisig_fingerprint.output_matches(txo):
            return False
        return (
            self.wallet_path.output_matches(txo)
            and txo.address_n[-2] <= _BIP32_CHANGE_CHAIN
            and txo.address_n[-1] <= _BIP32_MAX_LAST_ELEMENT
        )

    # Tx Inputs
    # ===

    def input_derive_script(
        self, txi: TxInputType, pubkey: bytes, signature: bytes = None
    ) -> bytes:
        return scripts.input_derive_script(
            txi, self.coin, self.get_hash_type(), pubkey, signature
        )


def input_is_segwit(txi: TxInputType) -> bool:
    return txi.script_type in helpers.SEGWIT_INPUT_SCRIPT_TYPES


def input_is_nonsegwit(txi: TxInputType) -> bool:
    return txi.script_type in helpers.NONSEGWIT_INPUT_SCRIPT_TYPES
