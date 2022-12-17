import gc
from micropython import const
from typing import TYPE_CHECKING

from trezor import log
from trezor.crypto.hashlib import blake2b
from trezor.enums import RequestType, ZcashSignatureType
from trezor.messages import TxRequest, ZcashAck, ZcashOrchardInput, ZcashOrchardOutput
from trezor.wire import DataError

from apps.bitcoin.sign_tx import helpers
from core.src.apps.common.paths import PathSchema

from .. import unified
from ..hasher import ZcashHasher
from ..layout import ConfirmOrchardInputsCountOverThreshold, UiConfirmForeignPath
from .accumulator import MessageAccumulator
from .crypto import builder, redpallas
from .crypto.address import Address
from .crypto.note import Note
from .debug import watch_gc_async
from .keychain import PATTERN_ZIP32, OrchardKeychain
from .random import BundleShieldingRng

if TYPE_CHECKING:
    from typing import Awaitable
    from apps.common.coininfo import CoinInfo
    from apps.common.paths import Bip32Path
    from apps.bitcoin.sign_tx.tx_info import TxInfo
    from .crypto.keys import FullViewingKey
    from ..approver import ZcashApprover
    from .random import ActionShieldingRng


OVERWINTERED = const(0x8000_0000)
FLAGS = const(0b0000_0011)  # spends enbled and output enabled
MAX_SILENT_ORCHARD_INPUTS = const(8)


class OrchardSigner:
    def __init__(
        self,
        tx_info: TxInfo,
        seed: bytes,
        approver: ZcashApprover,
        coin: CoinInfo,
        tx_req: TxRequest,
    ) -> None:
        assert tx_info.tx.orchard_params is not None  # checked in sanitize_sign_tx
        self.params = tx_info.tx.orchard_params
        self.actions_count = max(
            2,  # minimal required amount of actions
            self.params.inputs_count,
            self.params.outputs_count,
        )

        self.tx_info = tx_info
        self.keychain = OrchardKeychain(seed, coin)
        self.approver = approver
        self.coin = coin
        self.tx_req = tx_req
        assert isinstance(tx_info.sig_hasher, ZcashHasher)
        self.sig_hasher: ZcashHasher = tx_info.sig_hasher
        self.key_node = self.keychain.derive(self.params.address_n)

        self.msg_acc = MessageAccumulator(
            self.keychain.derive_slip21(
                [b"Zcash Orchard", b"Message Accumulator"],
            ).key()
        )

        self.rng = None

    async def process_inputs(self) -> None:
        await self.check_orchard_inputs_count()
        if not PathSchema.parse(PATTERN_ZIP32, self.coin.slip44).match(
            self.params.address_n
        ):
            await confirm_foreign_path(self.params.address_n)
        for i in range(self.params.inputs_count):
            txi = await self.get_input(i)
            self.msg_acc.xor_message(txi, i)  # add message to the accumulator
            self.approver.add_orchard_input(txi)

    def check_orchard_inputs_count(self) -> Awaitable[None]:  # type: ignore [awaitable-is-generator]
        # This check relates to the spend linkability dust attack
        # described in §6 of Attacking Zcash For Fun And Profit
        # https://eprint.iacr.org/2020/627
        #
        # The attack should be mitigated on the client side.
        # If it is not and a transaction has a suspiciously high
        # amount of inputs, then Trezor warns a user.
        #
        # Constant MAX_SILENT_ORCHARD_INPUTS is chosen heruistically.
        # According to the article, shielded transaction with >10 inputs
        # are quite unordinary and thus linkable.
        #
        # Since this attack is not severe, we don't abort.
        if self.params.inputs_count > MAX_SILENT_ORCHARD_INPUTS:
            yield ConfirmOrchardInputsCountOverThreshold(self.params.inputs_count)

    async def approve_outputs(self) -> None:
        for i in range(self.params.outputs_count):
            txo = await self.get_output(i)
            self.msg_acc.xor_message(txo, i)  # add message to the accumulator
            if output_is_internal(txo):
                self.approver.add_orchard_change_output(txo)
            else:
                await self.approver.add_orchard_external_output(txo)

    async def compute_digest(self) -> None:
        # derive shielding seed
        shielding_seed = self.derive_shielding_seed()
        self.rng = BundleShieldingRng(seed=shielding_seed)

        # send shielded_seed to the host
        assert self.tx_req.serialized is not None  # typing
        self.tx_req.serialized.zcash_shielding_seed = shielding_seed
        await self.release_serialized()

        # shuffle inputs
        inputs: list[int | None] = list(range(self.params.inputs_count))
        pad(inputs, self.actions_count)
        self.rng.shuffle_inputs(inputs)
        self.shuffled_inputs = inputs

        # shuffle_outputs
        outputs: list[int | None] = list(range(self.params.outputs_count))
        pad(outputs, self.actions_count)
        self.rng.shuffle_outputs(outputs)
        self.shuffled_outputs = outputs

        # precompute Full Viewing Key
        fvk = self.key_node.full_viewing_key()

        # shield and hash actions
        log.info(__name__, "start shielding")
        for i, (j, k) in enumerate(
            zip(
                self.shuffled_inputs,
                self.shuffled_outputs,
            )
        ):
            gc.collect()
            log.info(__name__, "shielding action %d (io: %s %s)", i, str(j), str(k))
            rng_i = self.rng.for_action(i)
            input_info = await self.build_input_info(j, fvk, rng_i)
            output_info = await self.build_output_info(k, fvk, rng_i)

            action = builder.build_action(input_info, output_info, rng_i)
            self.sig_hasher.orchard.add_action(action)

        log.info(__name__, "end shielding")

        # check that message accumulator is empty
        self.msg_acc.check()

        # hash orchard footer
        self.sig_hasher.orchard.finalize(
            flags=FLAGS,
            value_balance=self.approver.orchard_balance,
            anchor=self.params.anchor,
        )

    def derive_shielding_seed(self) -> bytes:
        ss_slip21 = self.keychain.derive_slip21(
            [b"Zcash Orchard", b"bundle_shielding_seed"],
        ).key()
        ss_hasher = blake2b(personal=b"TrezorShieldSeed", outlen=32)
        ss_hasher.update(self.sig_hasher.header.digest())
        ss_hasher.update(self.sig_hasher.transparent.digest())
        ss_hasher.update(self.msg_acc.state)
        ss_hasher.update(self.params.anchor)
        ss_hasher.update(ss_slip21)
        return ss_hasher.digest()

    @watch_gc_async
    async def build_input_info(
        self,
        index: int | None,
        fvk: FullViewingKey,
        rng: ActionShieldingRng,
    ) -> builder.InputInfo:
        if index is None:
            return builder.InputInfo.dummy(rng)

        txi = await self.get_input(index)
        self.msg_acc.xor_message(txi, index)  # remove message from the accumulator

        note = Note.from_message(txi)
        return builder.InputInfo(note, fvk)

    @watch_gc_async
    async def build_output_info(
        self,
        index: int | None,
        fvk: FullViewingKey,
        rng: ActionShieldingRng,
    ) -> builder.OutputInfo:
        if index is None:
            return builder.OutputInfo.dummy(rng)

        txo = await self.get_output(index)
        self.msg_acc.xor_message(txo, index)  # remove message from the accumulator

        if output_is_internal(txo):
            fvk = fvk.internal()
            address = fvk.address(0)
        else:
            assert txo.address is not None  # typing
            receivers = unified.decode_address(txo.address, self.coin)
            address = receivers.get(unified.Typecode.ORCHARD)
            if address is None:
                raise DataError("Address does not have an Orchard receiver.")
            address = Address.from_bytes(address)

        ovk = fvk.outgoing_viewing_key()
        return builder.OutputInfo(ovk, address, txo.amount, txo.memo)

    @watch_gc_async
    async def sign_inputs(self) -> None:
        sighash = self.sig_hasher.signature_digest()
        self.set_sighash(sighash)
        sig_type = ZcashSignatureType.ORCHARD_SPEND_AUTH
        ask = self.key_node.spend_authorizing_key()
        assert self.rng is not None
        for i, j in enumerate(self.shuffled_inputs):
            if j is None:
                continue
            rng = self.rng.for_action(i)
            rsk = redpallas.randomize(ask, rng.alpha())
            signature = redpallas.sign_spend_auth(rsk, sighash, rng)
            await self.set_serialized_signature(i, signature, sig_type)

    def set_sighash(self, sighash: bytes) -> None:
        assert self.tx_req.serialized is not None
        self.tx_req.serialized.tx_sighash = sighash

    async def set_serialized_signature(
        self, i: int, signature: bytes, sig_type: ZcashSignatureType
    ) -> None:
        assert self.tx_req.serialized is not None
        s = self.tx_req.serialized
        if s.signature_index is not None:
            await self.release_serialized()
        s.signature_index = i
        s.signature = signature
        s.signature_type = sig_type

    def get_input(self, i) -> Awaitable[ZcashOrchardInput]:  # type: ignore [awaitable-is-generator]
        self.tx_req.request_type = RequestType.TXORCHARDINPUT
        assert self.tx_req.details  # typing
        self.tx_req.details.request_index = i
        txi = yield ZcashOrchardInput, self.tx_req
        helpers._clear_tx_request(self.tx_req)
        return txi

    def get_output(self, i: int) -> Awaitable[ZcashOrchardOutput]:  # type: ignore [awaitable-is-generator]
        self.tx_req.request_type = RequestType.TXORCHARDOUTPUT
        assert self.tx_req.details is not None  # typing
        self.tx_req.details.request_index = i
        txo = yield ZcashOrchardOutput, self.tx_req
        helpers._clear_tx_request(self.tx_req)
        return txo

    def release_serialized(self) -> Awaitable[None]:  # type: ignore [awaitable-is-generator]
        self.tx_req.request_type = RequestType.NO_OP
        res = yield ZcashAck, self.tx_req
        helpers._clear_tx_request(self.tx_req)
        return res


def pad(items: list[int | None], target_length: int) -> None:
    items.extend((target_length - len(items)) * [None])


def output_is_internal(txo: ZcashOrchardOutput) -> bool:
    return txo.address is None


def confirm_foreign_path(path: Bip32Path) -> Awaitable[Any]:  # type: ignore [awaitable-is-generator]
    yield UiConfirmForeignPath(path)
