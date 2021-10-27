from micropython import const

from trezor import wire
from trezor.crypto.hashlib import sha256
from trezor.enums import InputScriptType, OutputScriptType
from trezor.messages import TxRequest, TxRequestDetailsType, TxRequestSerializedType
from trezor.utils import HashWriter, empty_bytearray, ensure

from apps.common.writers import write_bitcoin_varint

from .. import addresses, common, multisig, scripts, writers
from ..common import SIGHASH_ALL, ecdsa_sign, input_is_external, input_is_segwit
from ..ownership import verify_nonownership
from ..verification import SignatureVerifier
from . import approvers, helpers, progress
from .hash143 import Bip143Hash
from .tx_info import OriginalTxInfo, TxInfo

if False:
    from typing import Sequence

    from trezor.crypto import bip32

    from trezor.messages import (
        PrevInput,
        PrevOutput,
        PrevTx,
        SignTx,
        TxInput,
        TxOutput,
    )

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain

    from .hash143 import Hash143


# the number of bytes to preallocate for serialized transaction chunks
_MAX_SERIALIZED_CHUNK_SIZE = const(2048)
_SERIALIZED_TX_BUFFER = empty_bytearray(_MAX_SERIALIZED_CHUNK_SIZE)


class Bitcoin:
    async def signer(self) -> None:
        # Add inputs to hash143 and h_tx_check and compute the sum of input amounts.
        await self.step1_process_inputs()

        # Approve the original TXIDs in case of a replacement transaction.
        await self.approver.approve_orig_txids(self.tx_info, self.orig_txs)

        # Add outputs to hash143 and h_tx_check, approve outputs and compute
        # sum of output amounts.
        await self.step2_approve_outputs()

        # Check fee, approve lock_time and total.
        await self.approver.approve_tx(self.tx_info, self.orig_txs)

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
        keychain: Keychain,
        coin: CoinInfo,
        approver: approvers.Approver | None,
    ) -> None:
        global _SERIALIZED_TX_BUFFER

        self.tx_info = TxInfo(self, helpers.sanitize_sign_tx(tx, coin))
        self.keychain = keychain
        self.coin = coin

        if approver is not None:
            self.approver = approver
        else:
            self.approver = approvers.BasicApprover(tx, coin)

        # set of indices of inputs which are segwit
        self.segwit: set[int] = set()

        # set of indices of inputs which are external
        self.external: set[int] = set()

        # transaction and signature serialization
        _SERIALIZED_TX_BUFFER[:] = bytes()
        self.serialized_tx = _SERIALIZED_TX_BUFFER
        self.tx_req = TxRequest()
        self.tx_req.details = TxRequestDetailsType()
        self.tx_req.serialized = TxRequestSerializedType()
        self.tx_req.serialized.serialized_tx = self.serialized_tx

        # List of original transactions which are being replaced by the current transaction.
        # Note: A List is better than a Dict of TXID -> OriginalTxInfo. Dict ordering is
        # undefined so we would need to convert to a sorted list in several places to ensure
        # stable device tests.
        self.orig_txs: list[OriginalTxInfo] = []

        # h_inputs is a digest of the inputs streamed for approval in Step 1, which
        # is used to ensure that the inputs streamed for verification in Step 3 are
        # the same as those in Step 1.
        self.h_inputs: bytes | None = None

        progress.init(tx.inputs_count, tx.outputs_count)

    def create_hash_writer(self) -> HashWriter:
        return HashWriter(sha256())

    def create_hash143(self) -> Hash143:
        return Bip143Hash()

    async def step1_process_inputs(self) -> None:
        for i in range(self.tx_info.tx.inputs_count):
            # STAGE_REQUEST_1_INPUT in legacy
            txi = await helpers.request_tx_input(self.tx_req, i, self.coin)

            self.tx_info.add_input(txi)

            if input_is_segwit(txi):
                self.segwit.add(i)

            if input_is_external(txi):
                self.external.add(i)
                await self.process_external_input(txi)
            else:
                await self.process_internal_input(txi)

            if txi.orig_hash:
                await self.process_original_input(txi)

        self.h_inputs = self.tx_info.get_tx_check_digest()

        # Finalize original inputs.
        for orig in self.orig_txs:
            if orig.index != orig.tx.inputs_count:
                raise wire.ProcessError("Removal of original inputs is not supported.")

            orig.index = 0  # Reset counter for outputs.

    async def step2_approve_outputs(self) -> None:
        for i in range(self.tx_info.tx.outputs_count):
            # STAGE_REQUEST_2_OUTPUT in legacy
            txo = await helpers.request_tx_output(self.tx_req, i, self.coin)
            script_pubkey = self.output_derive_script(txo)
            orig_txo: TxOutput | None = None
            if txo.orig_hash:
                orig_txo = await self.get_original_output(txo, script_pubkey)
            await self.approve_output(txo, script_pubkey, orig_txo)

        # Finalize original outputs.
        for orig in self.orig_txs:
            # Fetch remaining removed original outputs.
            await self.fetch_removed_original_outputs(
                orig, orig.orig_hash, orig.tx.outputs_count
            )
            await orig.finalize_tx_hash()

    async def step3_verify_inputs(self) -> None:
        # should come out the same as h_inputs, checked before continuing
        h_check = HashWriter(sha256())

        for i in range(self.tx_info.tx.inputs_count):
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

        # verify the signature of one SIGHASH_ALL input in each original transaction
        await self.verify_original_txs()

    async def step4_serialize_inputs(self) -> None:
        self.write_tx_header(self.serialized_tx, self.tx_info.tx, bool(self.segwit))
        write_bitcoin_varint(self.serialized_tx, self.tx_info.tx.inputs_count)
        for i in range(self.tx_info.tx.inputs_count):
            progress.advance()
            if i in self.external:
                await self.serialize_external_input(i)
            elif i in self.segwit:
                await self.serialize_segwit_input(i)
            else:
                await self.sign_nonsegwit_input(i)

    async def step5_serialize_outputs(self) -> None:
        write_bitcoin_varint(self.serialized_tx, self.tx_info.tx.outputs_count)
        for i in range(self.tx_info.tx.outputs_count):
            progress.advance()
            await self.serialize_output(i)

    async def step6_sign_segwit_inputs(self) -> None:
        if not self.segwit:
            progress.advance(self.tx_info.tx.inputs_count)
            return

        for i in range(self.tx_info.tx.inputs_count):
            progress.advance()
            if i in self.segwit:
                if i in self.external:
                    txi = await helpers.request_tx_input(self.tx_req, i, self.coin)
                    self.serialized_tx.extend(txi.witness or b"\0")
                else:
                    await self.sign_segwit_input(i)
            else:
                # add empty witness for non-segwit inputs
                self.serialized_tx.append(0)

    async def step7_finish(self) -> None:
        self.write_tx_footer(self.serialized_tx, self.tx_info.tx)
        await helpers.request_tx_finish(self.tx_req)

    async def process_internal_input(self, txi: TxInput) -> None:
        if txi.script_type not in common.INTERNAL_INPUT_SCRIPT_TYPES:
            raise wire.DataError("Wrong input script type")

        await self.approver.add_internal_input(txi)

    async def process_external_input(self, txi: TxInput) -> None:
        self.approver.add_external_input(txi)

    async def process_original_input(self, txi: TxInput) -> None:
        assert txi.orig_hash is not None
        assert txi.orig_index is not None

        for orig in self.orig_txs:
            if orig.orig_hash == txi.orig_hash:
                break
        else:
            orig_meta = await helpers.request_tx_meta(
                self.tx_req, self.coin, txi.orig_hash
            )
            orig = OriginalTxInfo(self, orig_meta, txi.orig_hash)
            self.orig_txs.append(orig)

        if txi.orig_index >= orig.tx.inputs_count:
            raise wire.ProcessError("Not enough inputs in original transaction.")

        if orig.index != txi.orig_index:
            raise wire.ProcessError(
                "Rearranging or removal of original inputs is not supported."
            )

        orig_txi = await helpers.request_tx_input(
            self.tx_req, txi.orig_index, self.coin, txi.orig_hash
        )

        # Verify that the original input matches:
        # An input is characterized by its prev_hash and prev_index. We also check that the
        # amounts match, so that we don't have to call get_prevtx_output() twice for the same
        # prevtx output. Verifying that script_type matches is just a sanity check, because
        # because we count both inputs as internal or external based only on txi.script_type.
        if (
            orig_txi.prev_hash != txi.prev_hash
            or orig_txi.prev_index != txi.prev_index
            or orig_txi.amount != txi.amount
            or orig_txi.script_type != txi.script_type
        ):
            raise wire.ProcessError("Original input does not match current input.")

        orig.add_input(orig_txi)
        orig.index += 1

    async def fetch_removed_original_outputs(
        self, orig: OriginalTxInfo, orig_hash: bytes, last_index: int
    ) -> None:
        while orig.index < last_index:
            txo = await helpers.request_tx_output(
                self.tx_req, orig.index, self.coin, orig_hash
            )
            orig.add_output(txo, self.output_derive_script(txo))

            if orig.output_is_change(txo):
                # Removal of change-outputs is allowed.
                self.approver.add_orig_change_output(txo)
            else:
                # Removal of external outputs requires prompting the user. Not implemented.
                raise wire.ProcessError(
                    "Removal of original external outputs is not supported."
                )

            orig.index += 1

    async def get_original_output(
        self, txo: TxOutput, script_pubkey: bytes
    ) -> TxOutput:
        assert txo.orig_hash is not None
        assert txo.orig_index is not None

        for orig in self.orig_txs:
            if orig.orig_hash == txo.orig_hash:
                break
        else:
            raise wire.ProcessError("Unknown original transaction.")

        if txo.orig_index >= orig.tx.outputs_count:
            raise wire.ProcessError("Not enough outputs in original transaction.")

        if orig.index > txo.orig_index:
            raise wire.ProcessError("Rearranging of original outputs is not supported.")

        # First fetch any removed original outputs which precede the one we want.
        await self.fetch_removed_original_outputs(orig, txo.orig_hash, txo.orig_index)

        orig_txo = await helpers.request_tx_output(
            self.tx_req, orig.index, self.coin, txo.orig_hash
        )

        if script_pubkey != self.output_derive_script(orig_txo):
            raise wire.ProcessError("Not an original output.")

        if self.tx_info.output_is_change(txo) and not orig.output_is_change(orig_txo):
            raise wire.ProcessError(
                "Original output is missing change-output parameters."
            )

        orig.add_output(orig_txo, script_pubkey)

        if orig.output_is_change(orig_txo):
            self.approver.add_orig_change_output(orig_txo)
        else:
            self.approver.add_orig_external_output(orig_txo)

        orig.index += 1

        return orig_txo

    async def verify_original_txs(self) -> None:
        for orig in self.orig_txs:
            if orig.verification_input is None:
                raise wire.ProcessError(
                    "Each original transaction must specify address_n for at least one input."
                )

            assert orig.verification_index is not None
            txi = orig.verification_input

            node = self.keychain.derive(txi.address_n)
            address = addresses.get_address(
                txi.script_type, self.coin, node, txi.multisig
            )
            script_pubkey = scripts.output_derive_script(address, self.coin)

            verifier = SignatureVerifier(
                script_pubkey, txi.script_sig, txi.witness, self.coin
            )
            verifier.ensure_hash_type(SIGHASH_ALL)
            tx_digest = await self.get_tx_digest(
                orig.verification_index,
                txi,
                orig,
                verifier.public_keys,
                verifier.threshold,
                script_pubkey,
            )
            verifier.verify(tx_digest)

    async def approve_output(
        self,
        txo: TxOutput,
        script_pubkey: bytes,
        orig_txo: TxOutput | None,
    ) -> None:
        if self.tx_info.output_is_change(txo):
            # Output is change and does not need approval.
            self.approver.add_change_output(txo, script_pubkey)
        else:
            await self.approver.add_external_output(txo, script_pubkey, orig_txo)

        self.tx_info.add_output(txo, script_pubkey)

    async def get_tx_digest(
        self,
        i: int,
        txi: TxInput,
        tx_info: TxInfo | OriginalTxInfo,
        public_keys: Sequence[bytes | memoryview],
        threshold: int,
        script_pubkey: bytes,
    ) -> bytes:
        if txi.witness:
            return tx_info.hash143.preimage_hash(
                txi,
                public_keys,
                threshold,
                tx_info.tx,
                self.coin,
                self.get_sighash_type(txi),
            )
        else:
            digest, _, _ = await self.get_legacy_tx_digest(i, tx_info, script_pubkey)
            return digest

    async def verify_external_input(
        self, i: int, txi: TxInput, script_pubkey: bytes
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
                i,
                txi,
                self.tx_info,
                verifier.public_keys,
                verifier.threshold,
                script_pubkey,
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

        if txi.script_type not in common.SEGWIT_INPUT_SCRIPT_TYPES:
            raise wire.ProcessError("Transaction has changed during signing")
        self.tx_info.check_input(txi)

        node = self.keychain.derive(txi.address_n)
        key_sign_pub = node.public_key()
        self.write_tx_input_derived(self.serialized_tx, txi, key_sign_pub, b"")

    def sign_bip143_input(self, txi: TxInput) -> tuple[bytes, bytes]:
        self.tx_info.check_input(txi)

        node = self.keychain.derive(txi.address_n)
        public_key = node.public_key()

        if txi.multisig:
            public_keys = multisig.multisig_get_pubkeys(txi.multisig)
            threshold = txi.multisig.m
        else:
            public_keys = [public_key]
            threshold = 1
        hash143_hash = self.tx_info.hash143.preimage_hash(
            txi,
            public_keys,
            threshold,
            self.tx_info.tx,
            self.coin,
            self.get_sighash_type(txi),
        )

        signature = ecdsa_sign(node, hash143_hash)

        return public_key, signature

    async def sign_segwit_input(self, i: int) -> None:
        # STAGE_REQUEST_SEGWIT_WITNESS in legacy
        txi = await helpers.request_tx_input(self.tx_req, i, self.coin)
        if txi.script_type not in common.SEGWIT_INPUT_SCRIPT_TYPES:
            raise wire.ProcessError("Transaction has changed during signing")

        public_key, signature = self.sign_bip143_input(txi)

        self.set_serialized_signature(i, signature)
        if txi.multisig:
            # find out place of our signature based on the pubkey
            signature_index = multisig.multisig_pubkey_index(txi.multisig, public_key)
            scripts.write_witness_multisig(
                self.serialized_tx,
                txi.multisig,
                signature,
                signature_index,
                self.get_hash_type(txi),
            )
        else:
            scripts.write_witness_p2wpkh(
                self.serialized_tx, signature, public_key, self.get_hash_type(txi)
            )

    async def get_legacy_tx_digest(
        self,
        index: int,
        tx_info: TxInfo | OriginalTxInfo,
        script_pubkey: bytes | None = None,
    ) -> tuple[bytes, TxInput, bip32.HDNode | None]:
        tx_hash = tx_info.orig_hash if isinstance(tx_info, OriginalTxInfo) else None

        # the transaction digest which gets signed for this input
        h_sign = self.create_hash_writer()
        # should come out the same as h_tx_check, checked before signing the digest
        h_check = HashWriter(sha256())

        self.write_tx_header(h_sign, tx_info.tx, witness_marker=False)
        write_bitcoin_varint(h_sign, tx_info.tx.inputs_count)

        for i in range(tx_info.tx.inputs_count):
            # STAGE_REQUEST_4_INPUT in legacy
            txi = await helpers.request_tx_input(self.tx_req, i, self.coin, tx_hash)
            writers.write_tx_input_check(h_check, txi)
            # Only the previous UTXO's scriptPubKey is included in h_sign.
            if i == index:
                txi_sign = txi
                node = None
                if not script_pubkey:
                    self.tx_info.check_input(txi)
                    node = self.keychain.derive(txi.address_n)
                    key_sign_pub = node.public_key()
                    if txi.multisig:
                        # Sanity check to ensure we are signing with a key that is included in the multisig.
                        multisig.multisig_pubkey_index(txi.multisig, key_sign_pub)

                    if txi.script_type == InputScriptType.SPENDMULTISIG:
                        assert txi.multisig is not None  # checked in sanitize_tx_input
                        script_pubkey = scripts.output_script_multisig(
                            multisig.multisig_get_pubkeys(txi.multisig),
                            txi.multisig.m,
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

        write_bitcoin_varint(h_sign, tx_info.tx.outputs_count)

        for i in range(tx_info.tx.outputs_count):
            # STAGE_REQUEST_4_OUTPUT in legacy
            txo = await helpers.request_tx_output(self.tx_req, i, self.coin, tx_hash)
            script_pubkey = self.output_derive_script(txo)
            self.write_tx_output(h_check, txo, script_pubkey)
            self.write_tx_output(h_sign, txo, script_pubkey)

        writers.write_uint32(h_sign, tx_info.tx.lock_time)
        writers.write_uint32(h_sign, self.get_sighash_type(txi_sign))

        # check that the inputs were the same as those streamed for approval
        if tx_info.get_tx_check_digest() != h_check.get_digest():
            raise wire.ProcessError("Transaction has changed during signing")

        tx_digest = writers.get_tx_hash(h_sign, double=self.coin.sign_hash_double)
        return tx_digest, txi_sign, node

    async def sign_nonsegwit_input(self, i: int) -> None:
        tx_digest, txi, node = await self.get_legacy_tx_digest(i, self.tx_info)
        assert node is not None

        # compute the signature from the tx digest
        signature = ecdsa_sign(node, tx_digest)

        # serialize input with correct signature
        self.write_tx_input_derived(
            self.serialized_tx, txi, node.public_key(), signature
        )
        self.set_serialized_signature(i, signature)

    async def serialize_output(self, i: int) -> None:
        # STAGE_REQUEST_5_OUTPUT in legacy
        txo = await helpers.request_tx_output(self.tx_req, i, self.coin)
        script_pubkey = self.output_derive_script(txo)
        self.write_tx_output(self.serialized_tx, txo, script_pubkey)

    async def get_prevtx_output(
        self, prev_hash: bytes, prev_index: int
    ) -> tuple[int, bytes]:
        amount_out = 0  # output amount

        # STAGE_REQUEST_3_PREV_META in legacy
        tx = await helpers.request_tx_meta(self.tx_req, self.coin, prev_hash)

        if tx.outputs_count <= prev_index:
            raise wire.ProcessError("Not enough outputs in previous transaction.")

        txh = self.create_hash_writer()

        # witnesses are not included in txid hash
        self.write_tx_header(txh, tx, witness_marker=False)
        write_bitcoin_varint(txh, tx.inputs_count)

        for i in range(tx.inputs_count):
            # STAGE_REQUEST_3_PREV_INPUT in legacy
            txi = await helpers.request_tx_prev_input(
                self.tx_req, i, self.coin, prev_hash
            )
            self.write_tx_input(txh, txi, txi.script_sig)

        write_bitcoin_varint(txh, tx.outputs_count)

        for i in range(tx.outputs_count):
            # STAGE_REQUEST_3_PREV_OUTPUT in legacy
            txo_bin = await helpers.request_tx_prev_output(
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

    def check_prevtx_output(self, txo_bin: PrevOutput) -> None:
        # Validations to perform on the UTXO when checking the previous transaction output amount.
        pass

    # Tx Helpers
    # ===

    def get_sighash_type(self, txi: TxInput) -> int:
        return SIGHASH_ALL

    def get_hash_type(self, txi: TxInput) -> int:
        """ Return the nHashType flags."""
        # The nHashType is the 8 least significant bits of the sighash type.
        # Some coins set the 24 most significant bits of the sighash type to
        # the fork ID value.
        return self.get_sighash_type(txi) & 0xFF

    def write_tx_input_derived(
        self,
        w: writers.Writer,
        txi: TxInput,
        pubkey: bytes,
        signature: bytes,
    ) -> None:
        writers.write_bytes_reversed(w, txi.prev_hash, writers.TX_HASH_SIZE)
        writers.write_uint32(w, txi.prev_index)
        scripts.write_input_script_prefixed(
            w,
            txi.script_type,
            txi.multisig,
            self.coin,
            self.get_hash_type(txi),
            pubkey,
            signature,
        )
        writers.write_uint32(w, txi.sequence)

    @staticmethod
    def write_tx_input(
        w: writers.Writer,
        txi: TxInput | PrevInput,
        script: bytes,
    ) -> None:
        writers.write_tx_input(w, txi, script)

    @staticmethod
    def write_tx_output(
        w: writers.Writer,
        txo: TxOutput | PrevOutput,
        script_pubkey: bytes,
    ) -> None:
        writers.write_tx_output(w, txo, script_pubkey)

    def write_tx_header(
        self,
        w: writers.Writer,
        tx: SignTx | PrevTx,
        witness_marker: bool,
    ) -> None:
        writers.write_uint32(w, tx.version)  # nVersion
        if witness_marker:
            write_bitcoin_varint(w, 0x00)  # segwit witness marker
            write_bitcoin_varint(w, 0x01)  # segwit witness flag

    def write_tx_footer(self, w: writers.Writer, tx: SignTx | PrevTx) -> None:
        writers.write_uint32(w, tx.lock_time)

    async def write_prev_tx_footer(
        self, w: writers.Writer, tx: PrevTx, prev_hash: bytes
    ) -> None:
        self.write_tx_footer(w, tx)

    def set_serialized_signature(self, index: int, signature: bytes) -> None:
        # Only one signature per TxRequest can be serialized.
        assert self.tx_req.serialized is not None
        ensure(self.tx_req.serialized.signature is None)

        self.tx_req.serialized.signature_index = index
        self.tx_req.serialized.signature = signature

    # Tx Outputs
    # ===

    def output_derive_script(self, txo: TxOutput) -> bytes:
        if txo.script_type == OutputScriptType.PAYTOOPRETURN:
            assert txo.op_return_data is not None  # checked in sanitize_tx_output
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

        assert txo.address is not None  # checked in sanitize_tx_output

        return scripts.output_derive_script(txo.address, self.coin)
