from trezor import protobuf
from trezor.crypto import random, orchardlib, hmac, hashlib
from trezor.messages import (
    PrevTx, SignTx, TxRequest,
    ZcashOrchardData,
    ZcashOrchardInput,
    ZcashOrchardOutput,
)

from trezor.utils import BufferReader

from trezor.enums import RequestType, ZcashHMACType as hmac_type
from trezor.wire import ProcessError, DataError


from apps.common.coininfo import CoinInfo
from apps.common.writers import (
    write_compact_size,
    write_uint32_le,
    write_bytes_fixed,
)
from apps.common import readers
from apps.common.paths import HARDENED

from apps.bitcoin.sign_tx.bitcoinlike import Bitcoinlike
from apps.bitcoin.sign_tx import approvers, helpers

from apps import zcash  # TODO: beautify 

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Sequence
    from apps.common import coininfo
    from apps.bitcoin.sign_tx.tx_info import OriginalTxInfo, TxInfo
    from apps.bitcoin.writers import Writer


OVERWINTERED = 1 << 31


def skip_if_empty(func):
    async def wrapper(self):
        if self.actions_count == 0:
            return
        else:
            await func(self)
    return wrapper


class OrchardSigner:
    def __init__(
        self,
        tx_info: TxInfo,
        keychain: OrchardKeychain,
        approver: approvers.Approver,
        coin: CoinInfo,
        tx_req: TxRequest,
    ) -> None:
        self.inputs_count = tx_info.tx.orchard.inputs_count
        self.outputs_count = tx_info.tx.orchard.outputs_count

        self.actions_count = max(
            2,  # minimal required amount of actions
            self.inputs_count,
            self.outputs_count,
        ) if self.inputs_count + self.outputs_count > 0 else 0

        if self.actions_count == 0:
            return  # no need to create other attributes

        self.tx_info = tx_info
        self.keychain = keychain
        self.approver = approver
        self.tx_req = tx_req

        self.tx_req.serialized.orchard = ZcashOrchardData()

        account = tx_info.tx.orchard.account
        key_path = [
            32          | HARDENED,  # ZIP-32 constant
            coin.slip44 | HARDENED,  # purpose
            account     | HARDENED,  # account
        ]
        self.key_node = keychain.derive(key_path)

        self.alphas = []  # TODO: request alphas from the client
        self.hmac_secret = random.bytes(32)

    @skip_if_empty
    async def process_flags(self):
        enable_spends = self.tx_info.tx.orchard.enable_spends
        enable_outputs = self.tx_info.tx.orchard.enable_outputs
        if not enable_spends and self.inputs_count != 0:
            raise ProcessError("Spends disabled.")
        if not enable_outputs and self.outputs_count != 0:
            raise ProcessError("Outputs disabled.")

        if not enable_spends or not enable_outputs:  # non-standart situation
            yield layout.UiConfirmOrchardFlags(enable_spends, enable_outputs)

        # Orchard flags as defined in protocol §7.1 tx v5 format
        spends_flag = 0x01 if enable_spends else 0x00
        outputs_flag = 0x02 if enable_outputs else 0x00
        self.flags = bytes([spends_flag | outputs_flag])  # one byte

    async def process_inputs(self):
        for i in range(self.inputs_count):
            txi = await self.get_input(i)
            self.set_hmac(txi, hmac_type.ORCHARD_INPUT, i)

            self.approver.add_orchard_input(txi)

    async def approve_outputs(self):
        for i in range(self.outputs_count):
            txo = await self.get_output(i)
            self.set_hmac(txo, hmac_type.ORCHARD_OUTPUT, i)

            if txo.internal:
                self.approver.add_orchard_change_output(txo)
            else:
                await self.approver.add_orchard_external_output(txo)

    @skip_if_empty
    async def compute_digest(self):
        seed = self.set_seed()
        # `rand_state` is used by orchardlib to construct a PRG
        rand_state = {
            "seed": seed,
            "pos": 0,  # `pos` is modified by each orchardlib call
        }

        inputs = list(range(self.tx_info.tx.orchard.inputs_count))
        self.pad_and_shuffle(inputs, self.actions_count, rand_state)

        outputs = list(range(self.tx_info.tx.orchard.outputs_count))
        self.pad_and_shuffle(outputs, self.actions_count, rand_state)

        # precompute Full Viewing Key
        fvk = self.key_node.full_viewing_key()

        for i, j in zip(inputs, outputs):
            action_info = await self.build_action_info(i, j, fvk)
            action = orchardlib.shield(action_info, rand_state)  # on this line the magic happens
            self.tx_info.sig_hasher.orchard.add_action(action)
            self.alphas.append(action["alpha"])  # TODO: send alpha

        self.tx_info.sig_hasher.orchard.finalize(
            flags=self.flags,
            value_balance=self.approver.orchard_balance,
            anchor=self.tx_info.tx.orchard.anchor,
        )

    def set_seed(self):
        seed = random.bytes(32)
        assert self.tx_req.serialized.orchard.randomness_seed is None
        self.tx_req.serialized.orchard.randomness_seed = seed
        return seed

    def pad_and_shuffle(self, items, target_length, rand_state):
        items.extend((target_length - len(items))*[None])  # pad
        items_dict = dict(zip(range(target_length), items))
        items[:] = orchardlib.shuffle(items_dict, rand_state)  # shuffle 

    async def build_action_info(self, input_index, output_index, fvk):
        action_info = dict()

        if input_index is not None:
            txi = await self.get_input(input_index)
            self.verify_hmac(txi, hmac_type.ORCHARD_INPUT, input_index)

            action_info["spend_info"] = {
                "fvk": fvk.raw(internal=txi.internal),
                "note": txi.note,
            }

        if output_index is not None:
            txo = await self.get_output(output_index)
            self.verify_hmac(txo, hmac_type.ORCHARD_OUTPUT, output_index)

            if txo.internal:
                address = fvk.address(internal=True)
            else:
                receivers = zcash.address.decode_unified(txo.address)
                address = receivers.get(zcash.address.ORCHARD)
                if address is None:
                    raise ProcessError("Address has not an Orchard receiver.")

            action_info["output_info"] = {
                "ovk": fvk.outgoing_viewing_key(internal=txo.internal),
                "address": address,
                "value": txo.amount,
                "memo": txo.memo,
            }

        return action_info

    async def sign_inputs(self):
        for i in range(self.inputs_count):
            txi = await self.get_input(i)
            self.verify_hmac(txi, hmac_type.ORCHARD_INPUT, i)
            sk = self.key_node.spending_key()
            alpha = await self.get_alpha(i)
            sighash = self.tx_info.sig_hasher.signature_digest()
            signature = orchardlib.sign(sk, alpha, sighash)
            self.set_serialized_signature(i, signature)

    async def get_alpha(self, i):
        return self.alphas[i]

    def set_serialized_signature(self, i, signature):
        assert self.tx_req.serialized.orchard.signature_index is None
        self.tx_req.serialized.orchard.signature_index = i
        self.tx_req.serialized.orchard.signature = signature

    async def get_input(self, i):
        self.tx_req.request_type = RequestType.TXORCHARDINPUT
        self.tx_req.details.request_index = i
        txi = yield ZcashOrchardInput, self.tx_req
        helpers._clear_tx_request(self.tx_req)
        return _sanitize_input(txi)

    async def get_output(self, i):
        self.tx_req.request_type = RequestType.TXORCHARDOUTPUT
        self.tx_req.details.request_index = i
        txo = yield ZcashOrchardOutput, self.tx_req
        helpers._clear_tx_request(self.tx_req)
        return _sanitize_output(txo)

    def compute_hmac(self, msg, hmac_type, index):
        key_buffer = bytearray(32 + 4 + 4)
        write_bytes_fixed(key_buffer, self.hmac_secret, 32)
        write_uint32_le(key_buffer, hmac_type)
        write_uint32_le(key_buffer, index)
        key = hashlib.sha256(key_buffer).digest()

        mac = hmac(hmac.SHA256, key)
        mac.update(protobuf.dump_message_buffer(msg))
        return mac.digest()

    def set_hmac(self, msg, hmac_type, index):
        o = self.tx_req.serialized.orchard
        assert o.hmac is None
        o.hmac_type = hmac_type
        o.hmac_index = index
        o.hmac = self.compute_hmac(msg, hmac_type, index)

    def verify_hmac(self, msg, hmac_type, index):
        original_hmac = msg.hmac
        if original_hmac is None:
            raise ProcessError("Missing HMAC.")
        msg.hmac = None

        computed_hmac = self.compute_hmac(msg, hmac_type, index)

        if original_hmac != computed_hmac:
            raise ProcessError("Invalid HMAC.")


def _sanitize_input(txi: ZcashOrchardInput):
    # `txi.amount` equals `txi.orchard.note` value
    r = BufferReader(txi.note[43:51])
    txi.amount = readers.read_uint64_le(r)

    return txi


def _sanitize_output(txo: ZcashOrchardOutput):
    txo.internal = txo.address is None
    if txo.memo is not None:
        if len(txo.memo) != 512:
            ProcessError("Memo length must be 512 bytes.")

        # ZIP-302 Standardized Memo Field Format
        # (see https://zips.z.cash/zip-0302)
        if txo.memo[0] < 0xF5:
            try:
                txo.memo.rstrip(b"\x00").decode()
            except UnicodeDecodeError:
                raise ProcessError("Invalid memo encoding.")

        if txo.memo[0] == 0xF6:
            no_memo = True
            for i in range(1, 512):
                if txo.memo[i] != 0x00:
                    no_memo = False
                    break
            if no_memo:
                txo.memo = None

    return txo
