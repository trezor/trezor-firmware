from micropython import const

from trezor import wire
from trezor.crypto.hashlib import sha256
from trezor.messages import InputScriptType, OutputScriptType
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
from ..common import BIP32_WALLET_DEPTH, SIGHASH_ALL, ecdsa_sign
from ..ownership import verify_nonownership
from ..verification import SignatureVerifier
from . import approvers, helpers, progress
from .matchcheck import MultisigFingerprintChecker, WalletPathChecker

if False:
    from typing import List, Optional, Set, Tuple, Union
    from trezor.crypto.bip32 import HDNode

# the chain id used for change
_BIP32_CHANGE_CHAIN = const(1)

# the maximum allowed change address.  this should be large enough for normal
# use and still allow to quickly brute-force the correct bip32 path
_BIP32_MAX_LAST_ELEMENT = const(1000000)

# the number of bytes to preallocate for serialized transaction chunks
_MAX_SERIALIZED_CHUNK_SIZE = const(2048)


class Bitcoin:
    async def signer(self) -> None:
        # Add inputs to hash143 and h_approved and compute the sum of input amounts.
        await self.step1_process_inputs()

        # Add outputs to hash143 and h_approved, approve outputs and compute
        # sum of output amounts.
        await self.step2_approve_outputs()

        # Check fee, approve lock_time and total.
        await self.approver.approve_tx()

        # Verify the transaction input amounts by requesting each previous transaction
        # and checking its output amount. Verify external inputs which have already
        # been signed or which come with a proof of non-ownership.
        await self.step3_verify_inputs()

        # Check that inputs are unchanged. Serialize inputs and sign the non-segwit ones.
        await self.step4_serialize_inputs()

        # Serialize outputs.
        await self.step5_serialize_outputs()

        # Sign segwit inputs and serialize witness data.
        await self.step6_sign_segwit_inputs()

        # Write footer and send remaining data.
        await self.step7_finish()

    def __init__(
        self,
        tx: SignTx,
        keychain: seed.Keychain,
        coin: coininfo.CoinInfo,
        approver: approvers.Approver,
    ) -> None:
        self.tx = helpers.sanitize_sign_tx(tx, coin)
        self.keychain = keychain
        self.coin = coin
        self.approver = approver

        # checksum of multisig inputs, used to validate change-output
        self.multisig_fingerprint = MultisigFingerprintChecker()

        # common prefix of input paths, used to validate change-output
        self.wallet_path = WalletPathChecker()

        # set of indices of inputs which are segwit
        self.segwit = set()  # type: Set[int]

        # set of indices of inputs which are external
        self.external = set()  # type: Set[int]

        # transaction and signature serialization
        self.serialized_tx = writers.empty_bytearray(_MAX_SERIALIZED_CHUNK_SIZE)
        self.tx_req = TxRequest()
        self.tx_req.details = TxRequestDetailsType()
        self.tx_req.serialized = TxRequestSerializedType()
        self.tx_req.serialized.serialized_tx = self.serialized_tx

        # h_approved is used to make sure that the inputs and outputs streamed for
        # approval in Steps 1 and 2 are the same as the ones streamed for signing
        # legacy inputs in Step 4.
        self.h_approved = self.create_hash_writer()  # not a real tx hash

        # h_inputs is a digest of the inputs streamed for approval in Step 1, which
        # is used to ensure that the inputs streamed for verification in Step 3 are
        # the same as those in Step 1.
        self.h_inputs = None  # type: Optional[bytes]

        # BIP-0143 transaction hashing
        self.init_hash143()

        progress.init(self.tx.inputs_count, self.tx.outputs_count)

    def create_hash_writer(self) -> HashWriter:
        return HashWriter(sha256())

    async def step1_process_inputs(self) -> None:
        for i in range(self.tx.inputs_count):
            # STAGE_REQUEST_1_INPUT in legacy
            txi = await helpers.request_tx_input(self.tx_req, i, self.coin)

            self.hash143_add_input(txi)  # all inputs are included (non-segwit as well)
            writers.write_tx_input_check(self.h_approved, txi)

            if input_is_segwit(txi):
                self.segwit.add(i)

            if input_is_external(txi):
                self.external.add(i)
                await self.process_external_input(txi)
            else:
                await self.process_internal_input(txi)

        self.h_inputs = self.h_approved.get_digest()

    async def step2_approve_outputs(self) -> None:
        for i in range(self.tx.outputs_count):
            # STAGE_REQUEST_2_OUTPUT in legacy
            txo = await helpers.request_tx_output(self.tx_req, i, self.coin)
            script_pubkey = self.output_derive_script(txo)
            await self.approve_output(txo, script_pubkey)

    async def step3_verify_inputs(self) -> None:
        # should come out the same as h_inputs, checked before continuing
        h_check = self.create_hash_writer()

        for i in range(self.tx.inputs_count):
            progress.advance()
            txi = await helpers.request_tx_input(self.tx_req, i, self.coin)

            writers.write_tx_input_check(h_check, txi)
            prev_amount, script_pubkey = await self.get_prevtx_output(
                txi.prev_hash, txi.prev_index
            )
            if prev_amount != txi.amount:
                raise wire.DataError("Invalid amount specified")

            if i in self.external:
                await self.verify_external_input(i, txi, script_pubkey)

        # check that the inputs were the same as those streamed for approval
        if h_check.get_digest() != self.h_inputs:
            raise wire.ProcessError("Transaction has changed during signing")

    async def step4_serialize_inputs(self) -> None:
        self.write_tx_header(self.serialized_tx, self.tx, bool(self.segwit))
        write_bitcoin_varint(self.serialized_tx, self.tx.inputs_count)

        for i in range(self.tx.inputs_count):
            progress.advance()
            if i in self.external:
                await self.serialize_external_input(i)
            elif i in self.segwit:
                await self.serialize_segwit_input(i)
            else:
                await self.sign_nonsegwit_input(i)

    async def step5_serialize_outputs(self) -> None:
        write_bitcoin_varint(self.serialized_tx, self.tx.outputs_count)
        for i in range(self.tx.outputs_count):
            progress.advance()
            await self.serialize_output(i)

    async def step6_sign_segwit_inputs(self) -> None:
        if not self.segwit:
            progress.advance(self.tx.inputs_count)
            return

        for i in range(self.tx.inputs_count):
            progress.advance()
            if i in self.segwit:
                if i in self.external:
                    txi = await helpers.request_tx_input(self.tx_req, i, self.coin)
                    self.serialized_tx.extend(txi.witness)
                else:
                    await self.sign_segwit_input(i)
            else:
                # add empty witness for non-segwit inputs
                self.serialized_tx.append(0)

    async def step7_finish(self) -> None:
        self.write_tx_footer(self.serialized_tx, self.tx)
        await helpers.request_tx_finish(self.tx_req)

    async def process_internal_input(self, txi: TxInputType) -> None:
        self.wallet_path.add_input(txi)
        self.multisig_fingerprint.add_input(txi)

        if txi.script_type not in common.INTERNAL_INPUT_SCRIPT_TYPES:
            raise wire.DataError("Wrong input script type")

        await self.approver.add_internal_input(txi)

    async def process_external_input(self, txi: TxInputType) -> None:
        self.approver.add_external_input(txi)

    async def approve_output(self, txo: TxOutputType, script_pubkey: bytes) -> None:
        if self.output_is_change(txo):
            # output is change and does not need approval
            self.approver.add_change_output(txo, script_pubkey)
        else:
            await self.approver.add_external_output(txo, script_pubkey)

        self.write_tx_output(self.h_approved, txo, script_pubkey)
        self.hash143_add_output(txo, script_pubkey)

    async def get_tx_digest(
        self,
        i: int,
        txi: TxInputType,
        public_keys: List[bytes],
        threshold: int,
        script_pubkey: bytes,
    ) -> bytes:
        if txi.witness:
            return self.hash143_preimage_hash(txi, public_keys, threshold)
        else:
            digest, _, _ = await self.get_legacy_tx_digest(i, script_pubkey)
            return digest

    async def verify_external_input(
        self, i: int, txi: TxInputType, script_pubkey: bytes
    ) -> None:
        if txi.ownership_proof:
            if not verify_nonownership(
                txi.ownership_proof,
                script_pubkey,
                txi.commitment_data,
                self.keychain,
                self.coin,
            ):
                raise wire.DataError("Invalid external input")
        else:
            verifier = SignatureVerifier(
                script_pubkey, txi.script_sig, txi.witness, self.coin
            )

            verifier.ensure_hash_type(self.get_hash_type(txi))

            tx_digest = await self.get_tx_digest(
                i, txi, verifier.public_keys, verifier.threshold, script_pubkey
            )
            verifier.verify(tx_digest)

    async def serialize_external_input(self, i: int) -> None:
        txi = await helpers.request_tx_input(self.tx_req, i, self.coin)
        if not input_is_external(txi):
            raise wire.ProcessError("Transaction has changed during signing")

        self.write_tx_input(self.serialized_tx, txi, txi.script_sig or bytes())

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
        self.wallet_path.check_input(txi)
        self.multisig_fingerprint.check_input(txi)

        node = self.keychain.derive(txi.address_n)
        public_key = node.public_key()

        if txi.multisig:
            public_keys = multisig.multisig_get_pubkeys(txi.multisig)
            threshold = txi.multisig.m
        else:
            public_keys = [public_key]
            threshold = 1
        hash143_hash = self.hash143_preimage_hash(txi, public_keys, threshold)

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
                scripts.witness_multisig(
                    txi.multisig, signature, signature_index, self.get_hash_type(txi)
                )
            )
        else:
            self.serialized_tx.extend(
                scripts.witness_p2wpkh(signature, public_key, self.get_hash_type(txi))
            )

    async def get_legacy_tx_digest(
        self, index: int, script_pubkey: Optional[bytes] = None
    ) -> Tuple[bytes, TxInputType, Optional[HDNode]]:
        # the transaction digest which gets signed for this input
        h_sign = self.create_hash_writer()
        # should come out the same as h_approved, checked before signing the digest
        h_check = self.create_hash_writer()

        self.write_tx_header(h_sign, self.tx, witness_marker=False)
        write_bitcoin_varint(h_sign, self.tx.inputs_count)

        for i in range(self.tx.inputs_count):
            # STAGE_REQUEST_4_INPUT in legacy
            txi = await helpers.request_tx_input(self.tx_req, i, self.coin)
            writers.write_tx_input_check(h_check, txi)
            # Only the previous UTXO's scriptPubKey is included in h_sign.
            if i == index:
                txi_sign = txi
                node = None
                if not script_pubkey:
                    self.wallet_path.check_input(txi)
                    self.multisig_fingerprint.check_input(txi)
                    node = self.keychain.derive(txi.address_n)
                    key_sign_pub = node.public_key()
                    if txi.multisig:
                        # Sanity check to ensure we are signing with a key that is included in the multisig.
                        multisig.multisig_pubkey_index(txi.multisig, key_sign_pub)

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
                self.write_tx_input(h_sign, txi, script_pubkey)
            else:
                self.write_tx_input(h_sign, txi, bytes())

        write_bitcoin_varint(h_sign, self.tx.outputs_count)

        for i in range(self.tx.outputs_count):
            # STAGE_REQUEST_4_OUTPUT in legacy
            txo = await helpers.request_tx_output(self.tx_req, i, self.coin)
            script_pubkey = self.output_derive_script(txo)
            self.write_tx_output(h_check, txo, script_pubkey)
            self.write_tx_output(h_sign, txo, script_pubkey)

        writers.write_uint32(h_sign, self.tx.lock_time)
        writers.write_uint32(h_sign, self.get_sighash_type(txi_sign))

        # check that the inputs were the same as those streamed for approval
        if self.h_approved.get_digest() != h_check.get_digest():
            raise wire.ProcessError("Transaction has changed during signing")

        tx_digest = writers.get_tx_hash(h_sign, double=self.coin.sign_hash_double)
        return tx_digest, txi_sign, node

    async def sign_nonsegwit_input(self, i: int) -> None:
        tx_digest, txi, node = await self.get_legacy_tx_digest(i)
        assert node is not None

        # compute the signature from the tx digest
        signature = ecdsa_sign(node, tx_digest)

        # serialize input with correct signature
        script_sig = self.input_derive_script(txi, node.public_key(), signature)
        self.write_tx_input(self.serialized_tx, txi, script_sig)
        self.set_serialized_signature(i, signature)

    async def serialize_output(self, i: int) -> None:
        # STAGE_REQUEST_5_OUTPUT in legacy
        txo = await helpers.request_tx_output(self.tx_req, i, self.coin)
        script_pubkey = self.output_derive_script(txo)
        self.write_tx_output(self.serialized_tx, txo, script_pubkey)

    async def get_prevtx_output(
        self, prev_hash: bytes, prev_index: int
    ) -> Tuple[int, bytes]:
        amount_out = 0  # output amount

        # STAGE_REQUEST_3_PREV_META in legacy
        tx = await helpers.request_tx_meta(self.tx_req, self.coin, prev_hash)

        if tx.outputs_cnt <= prev_index:
            raise wire.ProcessError("Not enough outputs in previous transaction.")

        txh = self.create_hash_writer()

        # witnesses are not included in txid hash
        self.write_tx_header(txh, tx, witness_marker=False)
        write_bitcoin_varint(txh, tx.inputs_cnt)

        for i in range(tx.inputs_cnt):
            # STAGE_REQUEST_3_PREV_INPUT in legacy
            txi = await helpers.request_tx_input(self.tx_req, i, self.coin, prev_hash)
            self.write_tx_input(txh, txi, txi.script_sig)

        write_bitcoin_varint(txh, tx.outputs_cnt)

        for i in range(tx.outputs_cnt):
            # STAGE_REQUEST_3_PREV_OUTPUT in legacy
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

    def get_sighash_type(self, txi: TxInputType) -> int:
        return SIGHASH_ALL

    def get_hash_type(self, txi: TxInputType) -> int:
        """ Return the nHashType flags."""
        # The nHashType is the 8 least significant bits of the sighash type.
        # Some coins set the 24 most significant bits of the sighash type to
        # the fork ID value.
        return self.get_sighash_type(txi) & 0xFF

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
            and len(txo.address_n) >= BIP32_WALLET_DEPTH
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
            txi.script_type,
            txi.multisig,
            self.coin,
            self.get_hash_type(txi),
            pubkey,
            signature,
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

    def hash143_add_output(self, txo: TxOutputType, script_pubkey: bytes) -> None:
        writers.write_tx_output(self.h_outputs, txo, script_pubkey)

    def hash143_preimage_hash(
        self, txi: TxInputType, public_keys: List[bytes], threshold: int
    ) -> bytes:
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
        script_code = scripts.bip143_derive_script_code(
            txi, public_keys, threshold, self.coin
        )
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
        writers.write_uint32(h_preimage, self.get_sighash_type(txi))

        return writers.get_tx_hash(h_preimage, double=self.coin.sign_hash_double)


def input_is_segwit(txi: TxInputType) -> bool:
    return txi.script_type in common.SEGWIT_INPUT_SCRIPT_TYPES or (
        txi.script_type == InputScriptType.EXTERNAL and txi.witness is not None
    )


def input_is_nonsegwit(txi: TxInputType) -> bool:
    return txi.script_type in common.NONSEGWIT_INPUT_SCRIPT_TYPES or (
        txi.script_type == InputScriptType.EXTERNAL and txi.witness is None
    )


def input_is_external(txi: TxInputType) -> bool:
    return txi.script_type == InputScriptType.EXTERNAL
