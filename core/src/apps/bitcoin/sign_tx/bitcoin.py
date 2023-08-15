from micropython import const
from typing import TYPE_CHECKING

from trezor import workflow
from trezor.crypto.hashlib import sha256
from trezor.enums import InputScriptType
from trezor.utils import HashWriter, empty_bytearray
from trezor.wire import DataError, ProcessError

from apps.common.writers import write_compact_size

from .. import addresses, common, multisig, scripts, writers
from ..common import SigHashType, ecdsa_sign, input_is_external
from ..ownership import verify_nonownership
from ..verification import SignatureVerifier
from . import helpers
from .approvers import CoinJoinApprover
from .helpers import request_tx_input, request_tx_output
from .progress import progress
from .tx_info import OriginalTxInfo

if TYPE_CHECKING:
    from typing import Sequence

    from trezor.crypto import bip32
    from trezor.messages import PrevInput, PrevOutput, PrevTx, SignTx, TxInput, TxOutput

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain

    from ..writers import Writer
    from . import approvers
    from .sig_hasher import SigHasher
    from .tx_info import TxInfo


# the number of bytes to preallocate for serialized transaction chunks
_MAX_SERIALIZED_CHUNK_SIZE = const(2048)
_SERIALIZED_TX_BUFFER = empty_bytearray(_MAX_SERIALIZED_CHUNK_SIZE)


class Bitcoin:
    async def signer(self) -> None:
        progress.init(
            self.tx_info.tx, is_coinjoin=isinstance(self.approver, CoinJoinApprover)
        )

        # Add inputs to sig_hasher and h_tx_check and compute the sum of input amounts.
        await self.step1_process_inputs()

        # Approve the original TXIDs in case of a replacement transaction.
        await self.approver.approve_orig_txids(self.tx_info, self.orig_txs)

        # Add outputs to sig_hasher and h_tx_check, approve outputs and compute
        # sum of output amounts.
        await self.step2_approve_outputs()

        # Check fee, approve lock_time and total.
        await self.approver.approve_tx(self.tx_info, self.orig_txs)

        progress.init_signing(
            len(self.external),
            len(self.segwit),
            len(self.presigned),
            self.taproot_only,
            self.serialize,
            self.coin,
            self.tx_info.tx,
            self.orig_txs,
        )

        # Following steps can take a long time, make sure autolock doesn't kick in.
        # This is set to True again after workflow is finished in start_default().
        workflow.autolock_interrupts_workflow = False

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
        from trezor.messages import (
            TxRequest,
            TxRequestDetailsType,
            TxRequestSerializedType,
        )

        from . import approvers
        from .tx_info import TxInfo

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

        # set of indices of inputs which are presigned
        self.presigned: set[int] = set()

        # indicates whether all internal inputs are Taproot
        self.taproot_only = True

        # transaction and signature serialization
        _SERIALIZED_TX_BUFFER[:] = bytes()
        self.serialized_tx = _SERIALIZED_TX_BUFFER
        self.serialize = tx.serialize
        self.tx_req = TxRequest()
        self.tx_req.details = TxRequestDetailsType()
        self.tx_req.serialized = TxRequestSerializedType()
        self.tx_req.serialized.serialized_tx = self.serialized_tx

        # List of original transactions which are being replaced by the current transaction.
        # Note: A List is better than a Dict of TXID -> OriginalTxInfo. Dict ordering is
        # undefined so we would need to convert to a sorted list in several places to ensure
        # stable device tests.
        self.orig_txs: list[OriginalTxInfo] = []

        # The digest of the presigned external inputs streamed for approval in Step 1. This is
        # used to ensure that the inputs streamed for verification in Step 3 are the same as
        # those in Step 1.
        self.h_presigned_inputs: bytes | None = None

        # The index of the payment request being processed.
        self.payment_req_index: int | None = None

    def create_hash_writer(self) -> HashWriter:
        return HashWriter(sha256())

    def create_sig_hasher(self, tx: SignTx | PrevTx) -> SigHasher:
        from .sig_hasher import BitcoinSigHasher

        return BitcoinSigHasher()

    async def step1_process_inputs(self) -> None:
        from ..common import input_is_segwit

        tx_info = self.tx_info  # local_cache_attribute
        h_presigned_inputs_check = HashWriter(sha256())

        for i in range(tx_info.tx.inputs_count):
            # STAGE_REQUEST_1_INPUT in legacy
            progress.advance()
            txi = await request_tx_input(self.tx_req, i, self.coin)
            if txi.script_type not in (
                InputScriptType.SPENDTAPROOT,
                InputScriptType.EXTERNAL,
            ):
                self.taproot_only = False

            if input_is_segwit(txi):
                self.segwit.add(i)

            if input_is_external(txi):
                node = None
                self.external.add(i)
                if txi.witness or txi.script_sig:
                    self.presigned.add(i)
                    writers.write_tx_input_check(h_presigned_inputs_check, txi)
                await self.process_external_input(txi)
            else:
                node = self.keychain.derive(txi.address_n)
                await self.process_internal_input(txi, node)

            script_pubkey = self.input_derive_script(txi, node)
            self.tx_info.add_input(txi, script_pubkey)

            if txi.orig_hash:
                await self.process_original_input(txi, script_pubkey)

        tx_info.h_inputs_check = tx_info.get_tx_check_digest()
        self.h_presigned_inputs = h_presigned_inputs_check.get_digest()

        # Finalize original inputs.
        for orig in self.orig_txs:
            orig.h_inputs_check = orig.get_tx_check_digest()
            if orig.index != orig.tx.inputs_count:
                raise ProcessError("Removal of original inputs is not supported.")

            orig.index = 0  # Reset counter for outputs.

    async def step2_approve_outputs(self) -> None:
        for i in range(self.tx_info.tx.outputs_count):
            # STAGE_REQUEST_2_OUTPUT in legacy
            progress.advance()
            txo = await request_tx_output(self.tx_req, i, self.coin)
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
        # should come out the same as h_inputs_check, checked before continuing
        h_check = HashWriter(sha256())

        if self.taproot_only:
            # All internal inputs are Taproot. We only need to verify presigned external inputs.
            # We can trust the amounts and scriptPubKeys, because if an invalid value is provided
            # then all issued signatures will be invalid.
            expected_digest = self.h_presigned_inputs
            for i in range(self.tx_info.tx.inputs_count):
                if i in self.presigned:
                    progress.advance()
                    txi = await request_tx_input(self.tx_req, i, self.coin)
                    writers.write_tx_input_check(h_check, txi)

                    # txi.script_pubkey checked in sanitize_tx_input
                    assert txi.script_pubkey is not None
                    await self.verify_presigned_external_input(
                        i, txi, txi.script_pubkey
                    )
        else:
            # There are internal non-Taproot inputs. We need to verify all inputs, because we can't
            # trust any amounts or scriptPubKeys. If we did, then an attacker who provides invalid
            # information about amounts, scriptPubKeys and/or script types may still obtain valid
            # signatures for legacy and SegWit v0 inputs. These valid signatures could be exploited
            # in subsequent signing operations to falsely claim externality of the already signed
            # inputs or to falsely claim that a transaction is a replacement of an already approved
            # transaction or to construct a valid transaction by combining signatures obtained in
            # multiple rounds of the attack.
            expected_digest = self.tx_info.h_inputs_check
            for i in range(self.tx_info.tx.inputs_count):
                txi = await request_tx_input(self.tx_req, i, self.coin)
                writers.write_tx_input_check(h_check, txi)

                prev_amount, script_pubkey = await self.get_prevtx_output(
                    txi.prev_hash, txi.prev_index
                )
                if prev_amount != txi.amount:
                    raise DataError("Invalid amount specified")

                if script_pubkey != self.input_derive_script(txi):
                    raise DataError("Input does not match scriptPubKey")

                if i in self.presigned:
                    await self.verify_presigned_external_input(i, txi, script_pubkey)

        # check that the inputs were the same as those streamed for approval
        if h_check.get_digest() != expected_digest:
            raise ProcessError("Transaction has changed during signing")

        # verify the signature of one SIGHASH_ALL input in each original transaction
        await self.verify_original_txs()

    async def step4_serialize_inputs(self) -> None:
        if self.serialize:
            self.write_tx_header(self.serialized_tx, self.tx_info.tx, bool(self.segwit))
            write_compact_size(self.serialized_tx, self.tx_info.tx.inputs_count)

        for i in range(self.tx_info.tx.inputs_count):
            if i in self.external:
                if self.serialize:
                    progress.advance()
                    await self.serialize_external_input(i)
            elif i in self.segwit:
                if self.serialize:
                    progress.advance()
                    await self.serialize_segwit_input(i)
            else:
                progress.advance()
                await self.sign_nonsegwit_input(i)

    async def step5_serialize_outputs(self) -> None:
        if not self.serialize:
            return

        write_compact_size(self.serialized_tx, self.tx_info.tx.outputs_count)
        for i in range(self.tx_info.tx.outputs_count):
            progress.advance()
            await self.serialize_output(i)

    async def step6_sign_segwit_inputs(self) -> None:
        if not self.segwit:
            return

        for i in range(self.tx_info.tx.inputs_count):
            if i in self.segwit:
                if i in self.external:
                    if self.serialize:
                        if i in self.presigned:
                            progress.advance()
                            txi = await request_tx_input(self.tx_req, i, self.coin)
                            self.serialized_tx.extend(txi.witness or b"\0")
                        else:
                            self.serialized_tx.append(0)
                else:
                    progress.advance()
                    await self.sign_segwit_input(i)
            else:
                # add empty witness for non-segwit inputs
                if self.serialize:
                    self.serialized_tx.append(0)

    async def step7_finish(self) -> None:
        if self.serialize:
            self.write_tx_footer(self.serialized_tx, self.tx_info.tx)
        if __debug__:
            progress.assert_finished()
        await helpers.request_tx_finish(self.tx_req)

    async def process_internal_input(self, txi: TxInput, node: bip32.HDNode) -> None:
        if txi.script_type not in common.INTERNAL_INPUT_SCRIPT_TYPES:
            raise DataError("Wrong input script type")

        await self.approver.add_internal_input(txi, node)

    async def process_external_input(self, txi: TxInput) -> None:
        assert txi.script_pubkey is not None  # checked in sanitize_tx_input

        self.approver.add_external_input(txi)

        if txi.ownership_proof:
            if not verify_nonownership(
                txi.ownership_proof,
                txi.script_pubkey,
                txi.commitment_data,
                self.keychain,
                self.coin,
            ):
                raise DataError("Invalid external input")

    async def process_original_input(self, txi: TxInput, script_pubkey: bytes) -> None:
        orig_hash = txi.orig_hash  # local_cache_attribute
        orig_index = txi.orig_index  # local_cache_attribute

        assert orig_hash is not None
        assert orig_index is not None

        for orig in self.orig_txs:
            if orig.orig_hash == orig_hash:
                break
        else:
            orig_meta = await helpers.request_tx_meta(self.tx_req, self.coin, orig_hash)
            orig = OriginalTxInfo(self, orig_meta, orig_hash)
            self.orig_txs.append(orig)

        if orig_index >= orig.tx.inputs_count:
            raise ProcessError("Not enough inputs in original transaction.")

        if orig.index != orig_index:
            raise ProcessError(
                "Rearranging or removal of original inputs is not supported."
            )

        orig_txi = await request_tx_input(self.tx_req, orig_index, self.coin, orig_hash)

        # Verify that the original input matches:
        #
        # An input is characterized by its prev_hash and prev_index. We also check that the
        # amounts match, so that we don't have to call get_prevtx_output() twice for the same
        # prevtx output. Verifying that script_type matches is just a sanity check, because we
        # count both inputs as internal or external based only on txi.script_type.
        #
        # When all inputs are taproot, we don't check the prevtxs, so we have to ensure that the
        # claims about the script_pubkey values and amounts remain consistent throughout.
        if (
            orig_txi.prev_hash != txi.prev_hash
            or orig_txi.prev_index != txi.prev_index
            or orig_txi.amount != txi.amount
            or orig_txi.script_type != txi.script_type
            or self.input_derive_script(orig_txi) != script_pubkey
        ):
            raise ProcessError("Original input does not match current input.")

        orig.add_input(orig_txi, script_pubkey)
        orig.index += 1

    async def fetch_removed_original_outputs(
        self, orig: OriginalTxInfo, orig_hash: bytes, last_index: int
    ) -> None:
        while orig.index < last_index:
            txo = await request_tx_output(self.tx_req, orig.index, self.coin, orig_hash)
            orig.add_output(txo, self.output_derive_script(txo))

            if orig.output_is_change(txo):
                # Removal of change-outputs is allowed.
                self.approver.add_orig_change_output(txo)
            else:
                # Removal of external outputs requires prompting the user. Not implemented.
                raise ProcessError(
                    "Removal of original external outputs is not supported."
                )

            orig.index += 1

    async def get_original_output(
        self, txo: TxOutput, script_pubkey: bytes
    ) -> TxOutput:
        orig_hash = txo.orig_hash  # local_cache_attribute
        orig_index = txo.orig_index  # local_cache_attribute

        assert orig_hash is not None
        assert orig_index is not None

        for orig in self.orig_txs:
            if orig.orig_hash == orig_hash:
                break
        else:
            raise ProcessError("Unknown original transaction.")

        if orig_index >= orig.tx.outputs_count:
            raise ProcessError("Not enough outputs in original transaction.")

        if orig.index > orig_index:
            raise ProcessError("Rearranging of original outputs is not supported.")

        # First fetch any removed original outputs which precede the one we want.
        await self.fetch_removed_original_outputs(orig, orig_hash, orig_index)

        orig_txo = await request_tx_output(
            self.tx_req, orig.index, self.coin, orig_hash
        )

        if script_pubkey != self.output_derive_script(orig_txo):
            raise ProcessError("Not an original output.")

        if self.tx_info.output_is_change(txo) and not orig.output_is_change(orig_txo):
            raise ProcessError("Original output is missing change-output parameters.")

        orig.add_output(orig_txo, script_pubkey)

        if orig.output_is_change(orig_txo):
            self.approver.add_orig_change_output(orig_txo)
        else:
            self.approver.add_orig_external_output(orig_txo)

        orig.index += 1

        return orig_txo

    async def verify_original_txs(self) -> None:
        for orig in self.orig_txs:
            # should come out the same as h_inputs_check, checked before continuing
            h_check = HashWriter(sha256())

            for i in range(orig.tx.inputs_count):
                progress.advance()
                txi = await request_tx_input(self.tx_req, i, self.coin, orig.orig_hash)
                writers.write_tx_input_check(h_check, txi)
                script_pubkey = self.input_derive_script(txi)
                verifier = SignatureVerifier(
                    script_pubkey, txi.script_sig, txi.witness, self.coin
                )
                verifier.ensure_hash_type(
                    (SigHashType.SIGHASH_ALL_TAPROOT, self.get_sighash_type(txi))
                )
                tx_digest = await self.get_tx_digest(
                    i,
                    txi,
                    orig,
                    verifier.public_keys,
                    verifier.threshold,
                    script_pubkey,
                )
                verifier.verify(tx_digest)

            # check that the inputs were the same as those streamed for approval
            if h_check.get_digest() != orig.h_inputs_check:
                raise ProcessError("Transaction has changed during signing")

    async def approve_output(
        self,
        txo: TxOutput,
        script_pubkey: bytes,
        orig_txo: TxOutput | None,
    ) -> None:
        payment_req_index = txo.payment_req_index  # local_cache_attribute
        approver = self.approver  # local_cache_attribute

        if payment_req_index != self.payment_req_index:
            if payment_req_index is None:
                self.approver.finish_payment_request()
            else:
                tx_ack_payment_req = await helpers.request_payment_req(
                    self.tx_req, payment_req_index
                )
                await approver.add_payment_request(tx_ack_payment_req, self.keychain)
            self.payment_req_index = payment_req_index

        if self.tx_info.output_is_change(txo):
            # Output is change and does not need approval.
            await approver.add_change_output(txo, script_pubkey)
        else:
            await approver.add_external_output(txo, script_pubkey, orig_txo)

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
            if common.input_is_taproot(txi):
                return tx_info.sig_hasher.hash341(
                    i,
                    tx_info.tx,
                    self.get_sighash_type(txi),
                )
            else:
                return tx_info.sig_hasher.hash143(
                    txi,
                    public_keys,
                    threshold,
                    tx_info.tx,
                    self.coin,
                    self.get_hash_type(txi),
                )
        else:
            digest, _, _ = await self.get_legacy_tx_digest(i, tx_info, script_pubkey)
            return digest

    async def verify_presigned_external_input(
        self, i: int, txi: TxInput, script_pubkey: bytes
    ) -> None:
        verifier = SignatureVerifier(
            script_pubkey, txi.script_sig, txi.witness, self.coin
        )

        verifier.ensure_hash_type(
            (SigHashType.SIGHASH_ALL_TAPROOT, self.get_sighash_type(txi))
        )

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
        txi = await request_tx_input(self.tx_req, i, self.coin)
        if not input_is_external(txi):
            raise ProcessError("Transaction has changed during signing")

        self.write_tx_input(self.serialized_tx, txi, txi.script_sig or bytes())

    async def serialize_segwit_input(self, i: int) -> None:
        # STAGE_REQUEST_SEGWIT_INPUT in legacy
        txi = await request_tx_input(self.tx_req, i, self.coin)

        if txi.script_type not in common.SEGWIT_INPUT_SCRIPT_TYPES:
            raise ProcessError("Transaction has changed during signing")
        self.tx_info.check_input(txi)

        if txi.script_type == InputScriptType.SPENDP2SHWITNESS:
            node = self.keychain.derive(txi.address_n)
            key_sign_pub = node.public_key()
        else:
            # Native SegWit has an empty scriptSig. Public key is not needed.
            key_sign_pub = b""

        self.write_tx_input_derived(self.serialized_tx, txi, key_sign_pub, b"")

    def sign_bip143_input(self, i: int, txi: TxInput) -> tuple[bytes, bytes]:
        if self.taproot_only:
            # Prevents an attacker from bypassing prev tx checking by providing a different
            # script type than the one that was provided during the confirmation phase.
            raise ProcessError("Transaction has changed during signing")

        node = self.keychain.derive(txi.address_n)
        public_key = node.public_key()

        if txi.multisig:
            public_keys = multisig.multisig_get_pubkeys(txi.multisig)
            threshold = txi.multisig.m
        else:
            public_keys = [public_key]
            threshold = 1

        hash143_digest = self.tx_info.sig_hasher.hash143(
            txi,
            public_keys,
            threshold,
            self.tx_info.tx,
            self.coin,
            self.get_hash_type(txi),
        )

        signature = ecdsa_sign(node, hash143_digest)

        return public_key, signature

    def sign_taproot_input(self, i: int, txi: TxInput) -> bytes:
        from ..common import bip340_sign

        sigmsg_digest = self.tx_info.sig_hasher.hash341(
            i,
            self.tx_info.tx,
            self.get_sighash_type(txi),
        )

        node = self.keychain.derive(txi.address_n)
        return bip340_sign(node, sigmsg_digest)

    async def sign_segwit_input(self, i: int) -> None:
        # STAGE_REQUEST_SEGWIT_WITNESS in legacy
        txi = await request_tx_input(self.tx_req, i, self.coin)
        self.tx_info.check_input(txi)
        self.approver.check_internal_input(txi)
        if txi.script_type not in common.SEGWIT_INPUT_SCRIPT_TYPES:
            raise ProcessError("Transaction has changed during signing")

        if txi.script_type == InputScriptType.SPENDTAPROOT:
            signature = self.sign_taproot_input(i, txi)
            if self.serialize:
                scripts.write_witness_p2tr(
                    self.serialized_tx, signature, self.get_sighash_type(txi)
                )
        else:
            public_key, signature = self.sign_bip143_input(i, txi)
            if self.serialize:
                if txi.multisig:
                    # find out place of our signature based on the pubkey
                    signature_index = multisig.multisig_pubkey_index(
                        txi.multisig, public_key
                    )
                    scripts.write_witness_multisig(
                        self.serialized_tx,
                        txi.multisig,
                        signature,
                        signature_index,
                        self.get_sighash_type(txi),
                    )
                else:
                    scripts.write_witness_p2wpkh(
                        self.serialized_tx,
                        signature,
                        public_key,
                        self.get_sighash_type(txi),
                    )

        self.set_serialized_signature(i, signature)

    async def get_legacy_tx_digest(
        self,
        index: int,
        tx_info: TxInfo | OriginalTxInfo,
        script_pubkey: bytes | None = None,
    ) -> tuple[bytes, TxInput, bip32.HDNode | None]:
        tx = tx_info.tx  # local_cache_attribute
        coin = self.coin  # local_cache_attribute

        tx_hash = tx_info.orig_hash if isinstance(tx_info, OriginalTxInfo) else None

        # the transaction digest which gets signed for this input
        h_sign = self.create_hash_writer()
        # should come out the same as h_tx_check, checked before signing the digest
        h_check = HashWriter(sha256())

        self.write_tx_header(h_sign, tx, witness_marker=False)
        write_compact_size(h_sign, tx.inputs_count)

        txi_sign = None
        node = None
        for i in range(tx.inputs_count):
            # STAGE_REQUEST_4_INPUT in legacy
            progress.advance()
            txi = await request_tx_input(self.tx_req, i, coin, tx_hash)
            writers.write_tx_input_check(h_check, txi)
            # Only the previous UTXO's scriptPubKey is included in h_sign.
            if i == index:
                txi_sign = txi
                if not script_pubkey:
                    self.tx_info.check_input(txi)
                    node = self.keychain.derive(txi.address_n)
                    key_sign_pub = node.public_key()
                    txi_multisig = txi.multisig  # local_cache_attribute
                    if txi_multisig:
                        # Sanity check to ensure we are signing with a key that is included in the multisig.
                        multisig.multisig_pubkey_index(txi_multisig, key_sign_pub)

                    if txi.script_type == InputScriptType.SPENDMULTISIG:
                        assert txi_multisig is not None  # checked in _sanitize_tx_input
                        script_pubkey = scripts.output_script_multisig(
                            multisig.multisig_get_pubkeys(txi_multisig),
                            txi_multisig.m,
                        )
                    elif txi.script_type == InputScriptType.SPENDADDRESS:
                        script_pubkey = scripts.output_script_p2pkh(
                            addresses.ecdsa_hash_pubkey(key_sign_pub, coin)
                        )
                    else:
                        raise ProcessError("Unknown transaction type")
                self.write_tx_input(h_sign, txi, script_pubkey)
            else:
                self.write_tx_input(h_sign, txi, bytes())

        if txi_sign is None:
            raise RuntimeError  # index >= tx_info_tx.inputs_count

        write_compact_size(h_sign, tx.outputs_count)

        for i in range(tx.outputs_count):
            # STAGE_REQUEST_4_OUTPUT in legacy
            progress.advance()
            txo = await request_tx_output(self.tx_req, i, coin, tx_hash)
            script_pubkey = self.output_derive_script(txo)
            self.write_tx_output(h_check, txo, script_pubkey)
            self.write_tx_output(h_sign, txo, script_pubkey)

        writers.write_uint32(h_sign, tx.lock_time)
        writers.write_uint32(h_sign, self.get_hash_type(txi_sign))

        # check that the inputs were the same as those streamed for approval
        if tx_info.get_tx_check_digest() != h_check.get_digest():
            raise ProcessError("Transaction has changed during signing")

        tx_digest = writers.get_tx_hash(h_sign, coin.sign_hash_double)
        return tx_digest, txi_sign, node

    async def sign_nonsegwit_input(self, i: int) -> None:
        if self.taproot_only:
            # Prevents an attacker from bypassing prev tx checking by providing a different
            # script type than the one that was provided during the confirmation phase.
            raise ProcessError("Transaction has changed during signing")

        tx_digest, txi, node = await self.get_legacy_tx_digest(i, self.tx_info)
        assert node is not None

        # compute the signature from the tx digest
        signature = ecdsa_sign(node, tx_digest)

        if self.serialize:
            # serialize input with correct signature
            self.write_tx_input_derived(
                self.serialized_tx, txi, node.public_key(), signature
            )
        self.set_serialized_signature(i, signature)

    async def serialize_output(self, i: int) -> None:
        # STAGE_REQUEST_5_OUTPUT in legacy
        txo = await request_tx_output(self.tx_req, i, self.coin)
        script_pubkey = self.output_derive_script(txo)
        self.write_tx_output(self.serialized_tx, txo, script_pubkey)

    async def get_prevtx_output(
        self, prev_hash: bytes, prev_index: int
    ) -> tuple[int, bytes]:
        coin = self.coin  # local_cache_attribute

        amount_out = 0  # output amount

        # STAGE_REQUEST_3_PREV_META in legacy
        tx = await helpers.request_tx_meta(self.tx_req, coin, prev_hash)
        progress.init_prev_tx(tx.inputs_count, tx.outputs_count)

        if tx.outputs_count <= prev_index:
            raise ProcessError("Not enough outputs in previous transaction.")

        txh = self.create_hash_writer()

        # witnesses are not included in txid hash
        self.write_tx_header(txh, tx, witness_marker=False)
        write_compact_size(txh, tx.inputs_count)

        for i in range(tx.inputs_count):
            # STAGE_REQUEST_3_PREV_INPUT in legacy
            progress.advance_prev_tx()
            txi = await helpers.request_tx_prev_input(self.tx_req, i, coin, prev_hash)
            self.write_tx_input(txh, txi, txi.script_sig)

        write_compact_size(txh, tx.outputs_count)

        script_pubkey: bytes | None = None
        for i in range(tx.outputs_count):
            # STAGE_REQUEST_3_PREV_OUTPUT in legacy
            progress.advance_prev_tx()
            txo_bin = await helpers.request_tx_prev_output(
                self.tx_req, i, coin, prev_hash
            )
            self.write_tx_output(txh, txo_bin, txo_bin.script_pubkey)
            if i == prev_index:
                amount_out = txo_bin.amount
                script_pubkey = txo_bin.script_pubkey
                self.check_prevtx_output(txo_bin)

        assert script_pubkey is not None  # prev_index < tx.outputs_count

        await self.write_prev_tx_footer(txh, tx, prev_hash)

        if writers.get_tx_hash(txh, coin.sign_hash_double, True) != prev_hash:
            raise ProcessError("Encountered invalid prev_hash")

        return amount_out, script_pubkey

    def check_prevtx_output(self, txo_bin: PrevOutput) -> None:
        # Validations to perform on the UTXO when checking the previous transaction output amount.
        pass

    # Tx Helpers
    # ===

    def get_hash_type(self, txi: TxInput) -> int:
        # The nHashType in BIP 143.
        if common.input_is_taproot(txi):
            return SigHashType.SIGHASH_ALL_TAPROOT
        else:
            return SigHashType.SIGHASH_ALL

    def get_sighash_type(self, txi: TxInput) -> SigHashType:
        """Return the nHashType flags."""
        # The nHashType is the 8 least significant bits of the sighash type.
        # Some coins set the 24 most significant bits of the sighash type to
        # the fork ID value.
        return self.get_hash_type(txi) & 0xFF  # type: ignore [int-into-enum]

    def write_tx_input_derived(
        self,
        w: Writer,
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
            self.get_sighash_type(txi),
            pubkey,
            signature,
        )
        writers.write_uint32(w, txi.sequence)

    @staticmethod
    def write_tx_input(
        w: Writer,
        txi: TxInput | PrevInput,
        script: bytes,
    ) -> None:
        writers.write_tx_input(w, txi, script)

    @staticmethod
    def write_tx_output(
        w: Writer,
        txo: TxOutput | PrevOutput,
        script_pubkey: bytes,
    ) -> None:
        writers.write_tx_output(w, txo, script_pubkey)

    def write_tx_header(
        self,
        w: Writer,
        tx: SignTx | PrevTx,
        witness_marker: bool,
    ) -> None:
        writers.write_uint32(w, tx.version)  # nVersion
        if witness_marker:
            write_compact_size(w, 0x00)  # segwit witness marker
            write_compact_size(w, 0x01)  # segwit witness flag

    def write_tx_footer(self, w: Writer, tx: SignTx | PrevTx) -> None:
        writers.write_uint32(w, tx.lock_time)

    async def write_prev_tx_footer(
        self, w: Writer, tx: PrevTx, prev_hash: bytes
    ) -> None:
        self.write_tx_footer(w, tx)

    def set_serialized_signature(self, index: int, signature: bytes) -> None:
        from trezor.utils import ensure

        serialized = self.tx_req.serialized  # local_cache_attribute

        # Only one signature per TxRequest can be serialized.
        assert serialized is not None
        ensure(serialized.signature is None)

        serialized.signature_index = index
        serialized.signature = signature

    # scriptPubKey derivation
    # ===

    def input_derive_script(
        self, txi: TxInput, node: bip32.HDNode | None = None
    ) -> bytes:
        if input_is_external(txi):
            assert txi.script_pubkey is not None  # checked in _sanitize_tx_input
            return txi.script_pubkey

        if node is None:
            node = self.keychain.derive(txi.address_n)

        address = addresses.get_address(txi.script_type, self.coin, node, txi.multisig)
        return scripts.output_derive_script(address, self.coin)

    def output_derive_script(self, txo: TxOutput) -> bytes:
        from trezor.enums import OutputScriptType

        if txo.script_type == OutputScriptType.PAYTOOPRETURN:
            assert txo.op_return_data is not None  # checked in _sanitize_tx_output
            return scripts.output_script_paytoopreturn(txo.op_return_data)

        if txo.address_n:
            # change output
            try:
                input_script_type = common.CHANGE_OUTPUT_TO_INPUT_SCRIPT_TYPES[
                    txo.script_type
                ]
            except KeyError:
                raise DataError("Invalid script type")
            node = self.keychain.derive(txo.address_n)
            txo.address = addresses.get_address(
                input_script_type, self.coin, node, txo.multisig
            )

        assert txo.address is not None  # checked in _sanitize_tx_output

        return scripts.output_derive_script(txo.address, self.coin)
