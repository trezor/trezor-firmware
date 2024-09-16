from typing import TYPE_CHECKING

from trezor.database import cache
from trezor.database.storage_database_context import StorageDatabaseContext
from trezor.messages import DatabaseMergeResponse
from trezor.ui.layouts import confirm_action

if TYPE_CHECKING:
    from trezor.messages import DatabaseMerge


async def merge(msg: DatabaseMerge) -> DatabaseMergeResponse:
    assert msg.database_time is not None
    assert msg.database_signature is not None
    assert msg.key is not None
    assert msg.value is not None
    assert msg.proof is not None
    assert msg.update_identifier is not None
    assert msg.update_time is not None
    assert msg.update_signature is not None

    async with StorageDatabaseContext() as database_context:
        # TODO: use translations
        if True:  # TODO: remove
            await confirm_action(
                "warning_database_set",
                "Database set",
                description=f"Do you want to set '{msg.key}' to '{msg.value}'?",
            )
        cache.wipe()

        signature = database_context.merge(
            msg.database_time,
            msg.database_signature,
            msg.key,
            msg.value,
            msg.proof,
            msg.update_identifier,
            msg.update_time,
            msg.update_signature,
        )

        cache.set(msg.key, msg.value)

    return DatabaseMergeResponse(database_signature=signature)
