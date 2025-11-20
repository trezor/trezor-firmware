from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EvoluGetNode, EvoluNode

_EVOLU_KEY_PATH_PREFIX = [b"TREZOR", b"Evolu"]


async def get_node(msg: EvoluGetNode) -> EvoluNode:
    """
    Returns the SLIP-21 node to generate Evolu keys for this passphrase.

    This function does not work if the device is not initialized.

    This function requires a proof of delegated identity.

    Args:
        msg (EvoluGetNode): The message containing parameters and proof of delegated identity.
    Returns:
        EvoluNode: The derived SLIP-21 node containing the necessary data for further key generation.
    Raises:
        NotInitialized: If the device is not initialized.
        ValueError: If the proof of delegated identity is missing or invalid.
    """
    from storage.device import is_initialized
    from trezor.messages import EvoluNode
    from trezor.wire import NotInitialized

    from .common import check_delegated_identity_proof

    if not is_initialized():
        raise NotInitialized("Device is not initialized")

    if not check_delegated_identity_proof(
        bytes(msg.proof_of_delegated_identity), header=b"EvoluGetNode"
    ):
        raise ValueError("Invalid proof")

    # TODO: adjust copy when the usage is exposed via Trezor Suite

    return EvoluNode(data=await derive_evolu_node(msg.index))


async def derive_evolu_node(index:int) -> bytes:
    from apps.common.seed import Slip21Node, get_seed

    seed = await get_seed()
    node = Slip21Node(seed)
    node.derive_path(_EVOLU_KEY_PATH_PREFIX + [index.to_bytes(4, "big")])

    return node.data
