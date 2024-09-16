from typing import TYPE_CHECKING

from trezor.database.storage_database_context import StorageDatabaseContext
from trezor.messages import DatabaseModifyKeyResponse
from trezor.ui.layouts import confirm_action

if TYPE_CHECKING:
    from trezor.messages import DatabaseModifyKey

from trezor.database import cache


async def modify_key(msg: DatabaseModifyKey) -> DatabaseModifyKeyResponse:
    assert msg.database_time is not None
    assert msg.database_signature is not None
    assert msg.key is not None
    assert msg.proof is not None

    # TODO: use translations
    if True:  # TODO: remove
        await confirm_action(
            "warning_database_set",
            "Database set",
            description=f"Do you want to set '{msg.key}' to '{msg.value}'?",
        )

    async with StorageDatabaseContext() as database_context:
        database_signature, update_signature = database_context.modify_key(
            msg.database_time,
            msg.database_signature,
            msg.key,
            msg.value,
            msg.proof,
        )

    cache.set(msg.key, msg.value)

    return DatabaseModifyKeyResponse(
        database_signature=database_signature, update_signature=update_signature
    )
