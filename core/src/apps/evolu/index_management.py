from typing import TYPE_CHECKING
from micropython import const

if TYPE_CHECKING:
    from trezor.messages import EvoluIndexManagement, EvoluIndexManagementResponse

ROTATION_INDEX_LIMIT = const((1 << 16) - 1)

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

    stored_index = get_delegated_identity_key_rotation_index()

    if stored_index is None:
        if msg.rotation_index is not None:
            if msg.rotation_index < 0 or msg.rotation_index > ROTATION_INDEX_LIMIT:
                raise ValueError(f"Rotation index must be between 0 and {ROTATION_INDEX_LIMIT}")
            set_delegated_identity_key_rotation_index(msg.rotation_index)
            stored_index = msg.rotation_index

    return EvoluIndexManagementResponse(rotation_index=stored_index)
