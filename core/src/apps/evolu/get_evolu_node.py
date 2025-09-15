from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EvoluGetNode, EvoluNode

_EVOLU_KEY_PATH_PREFIX = [b"TREZOR", b"Evolu"]


async def get_evolu_node(msg: EvoluGetNode) -> EvoluNode:
    from storage.device import is_initialized
    from trezor.messages import EvoluNode
    from trezor.wire import NotInitialized

    from .common import check_delegated_identity_key

    if not is_initialized():
        raise NotInitialized("Device is not initialized")

    if not check_delegated_identity_key(msg.proof, header=b"EvoluGetNode"):
        raise ValueError("Invalid proof")

    # TODO: adjust copy when the usage is exposed via Trezor Suite

    return EvoluNode(data=await derive_evolu_node())


async def derive_evolu_node() -> bytes:
    from apps.common.seed import Slip21Node, get_seed

    seed = await get_seed()
    node = Slip21Node(seed)
    node.derive_path(_EVOLU_KEY_PATH_PREFIX)

    return node.data
