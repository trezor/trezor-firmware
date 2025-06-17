from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EvoluGetNode, EvoluNode

_EVOLU_KEY_PATH_PREFIX = [b"TREZOR", b"Evolu"]


async def get_evolu_node(_msg: EvoluGetNode) -> EvoluNode:
    from storage.device import is_initialized
    from trezor.messages import EvoluNode
    from trezor.ui.layouts import confirm_action
    from trezor.wire import NotInitialized

    from apps.common.seed import Slip21Node, get_seed

    if not is_initialized():
        raise NotInitialized("Device is not initialized")

    # TODO: adjust copy when the usage is exposed via Trezor Suite
    await confirm_action(
        "get_evolu_keys",
        "Evolu node",
        action="Derive SLIP-21 node for Evolu?",
        prompt_screen=True,
    )
    seed = await get_seed()
    node = Slip21Node(seed)
    node.derive_path(_EVOLU_KEY_PATH_PREFIX)

    return EvoluNode(data=node.data)
