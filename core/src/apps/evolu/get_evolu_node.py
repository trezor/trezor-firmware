from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EvoluGetNode, EvoluNode

_EVOLU_KEY_PATH_PREFIX = [b"TREZOR", b"Evolu"]


async def get_evolu_node(msg: EvoluGetNode) -> EvoluNode:
    from storage.device import is_initialized
    from trezor import TR, utils, wire
    from trezor.messages import EvoluNode
    from trezor.ui.layouts import confirm_action
    from trezor.utils import bootloader_locked
    from trezor.wire import NotInitialized

    from .common import check_delegated_identity_proof

    if (
        bootloader_locked() is False
    ):  # cannot use `if not bootloader_locked()` since on None we do not want to raise an error
        raise wire.ProcessError(
            "Cannot provide Evolu node since bootloader is unlocked."
        )

    if not is_initialized():
        raise NotInitialized("Device is not initialized")

    if utils.USE_OPTIGA:
        if not msg.proof_of_delegated_identity:
            raise ValueError(
                "Proof of delegated identity must be provided when Optiga is available"
            )

        if not check_delegated_identity_proof(
            bytes(msg.proof_of_delegated_identity), header=b"EvoluGetNode"
        ):
            raise ValueError("Invalid proof")
    else:
        await confirm_action(
            "evolu_get_node_without_optiga",
            TR.evolu__enable_labeling_header,
            TR.evolu__enable_labeling_message_no_thp,
        )

    # TODO: adjust copy when the usage is exposed via Trezor Suite

    return EvoluNode(data=await derive_evolu_node())


async def derive_evolu_node() -> bytes:
    from apps.common.seed import Slip21Node, get_seed

    seed = await get_seed()
    node = Slip21Node(seed)
    node.derive_path(_EVOLU_KEY_PATH_PREFIX)

    return node.data
