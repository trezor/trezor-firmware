from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EvoluIndexManagement, EvoluIndexManagementResponse


async def index_management(msg: EvoluIndexManagement) -> EvoluIndexManagementResponse:
    """
    Sets the delegated identity key rotation index if it is not already set.
    Returns the current rotation index.
    """
    from storage.device import (
        get_delegated_identity_key_rotation_index,
        set_delegated_identity_key_rotation_index,
    )
    from trezor.messages import EvoluIndexManagementResponse

    from .common import ROTATION_INDEX_LIMIT, check_delegated_identity_rotation_index

    check_delegated_identity_rotation_index(msg.rotation_index)

    stored_index = get_delegated_identity_key_rotation_index()

    if stored_index is None:
        if msg.rotation_index is not None:
            if not 0 <= msg.rotation_index <= ROTATION_INDEX_LIMIT:
                raise ValueError(
                    f"Rotation index must be between 0 and {ROTATION_INDEX_LIMIT}"
                )
            set_delegated_identity_key_rotation_index(msg.rotation_index)
            stored_index = msg.rotation_index

    return EvoluIndexManagementResponse(rotation_index=stored_index)
