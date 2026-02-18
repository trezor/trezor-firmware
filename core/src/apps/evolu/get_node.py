from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EvoluGetNode, EvoluNode

_EVOLU_KEY_PATH_PREFIX = [b"TREZOR", b"Evolu"]
_EVOLU_KEY_PATH_PREFIX_INDEX = [b"TREZOR", b"Evolu Index"]


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
        bytes(msg.proof_of_delegated_identity),
        header=b"EvoluGetNode",
    ):
        raise ValueError("Invalid proof")

    # TODO: adjust copy when the usage is exposed via Trezor Suite

    index = msg.node_rotation_index or 0
    return EvoluNode(data=await derive_evolu_node(index))

# The `node_rotation_index` is NOT protected like the `delegated_identity_key_index`.
# A compromised application with access to the current `delegated_identity_key` can enumerate all possible nodes by calling this function with different indices.
#
# Rationale for this:
# 1. This index is dependent on passphrase and thus we cannot store the index on the device due to plausible deniability.
# 2. We cannot include the `delegated_identity_key_index` in the SLIP-21 path because we need to get the same node on the same seed regardless of the device.
#
# This index protects against a passive attacker who gains access to one of the nodes but not to the unlocked device.
# Rotating the node to a new index then restricts the attacker's ability to read new labels.
#
# Note: The need for node rotation has diminished recently as we now handle data deletion through other mechanisms.
async def derive_evolu_node(index: int) -> bytes:
    from apps.common.seed import Slip21Node, get_seed

    seed = await get_seed()
    node = Slip21Node(seed)
    if index == 0:
        node.derive_path(_EVOLU_KEY_PATH_PREFIX)
    else:
        node.derive_path(_EVOLU_KEY_PATH_PREFIX_INDEX + [str(index).encode()])

    return node.data
