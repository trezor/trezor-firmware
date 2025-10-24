from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EvoluGetNode, EvoluNode

_EVOLU_KEY_PATH_PREFIX = [b"TREZOR", b"Evolu"]


async def get_evolu_node(msg: EvoluGetNode) -> EvoluNode:
    """
    Returns the SLIP-21 node to generate Evolu keys for this passphrase.

    This function does not work if the bootloader is unlocked or if the device is not initialized.

    On devices with Optiga, this function requires a proof of delegated identity.

    On devices without Optiga, the user is prompted to confirm the issuance of the node every time.

    Args:
        msg (EvoluGetNode): The message containing parameters and optional proof of delegated identity.
    Returns:
        EvoluNode: The derived SLIP-21 node containing the necessary data for further key generation.
    Raises:
        ProcessError: If the bootloader is unlocked.
        NotInitialized: If the device is not initialized.
        ValueError: If Optiga is available but the proof of delegated identity is missing or invalid.
    """
    from storage.device import is_initialized
    from trezor import TR, utils
    from trezor.messages import EvoluNode
    from trezor.ui.layouts import confirm_action
    from trezor.utils import bootloader_locked
    from trezor.wire import NotInitialized, ProcessError

    from .common import check_delegated_identity_proof

    if (
        bootloader_locked() is False
    ):  # cannot use `if not bootloader_locked()` since on None we do not want to raise an error
        raise ProcessError("Cannot provide Evolu node since bootloader is unlocked.")

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
            TR.secure_sync__header,
            TR.secure_sync__evolu_node_no_optiga,
        )

    # TODO: adjust copy when the usage is exposed via Trezor Suite

    return EvoluNode(data=await derive_evolu_node())


async def derive_evolu_node() -> bytes:
    from apps.common.seed import Slip21Node, get_seed

    seed = await get_seed()
    node = Slip21Node(seed)
    node.derive_path(_EVOLU_KEY_PATH_PREFIX)

    return node.data
