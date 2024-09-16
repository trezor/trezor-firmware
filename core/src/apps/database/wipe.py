from typing import TYPE_CHECKING

from trezor.database import cache
from trezor.database.storage_database_context import StorageDatabaseContext
from trezor.messages import DatabaseWipeResponse
from trezor.ui.layouts import confirm_action

if TYPE_CHECKING:
    from trezor.messages import DatabaseWipe


async def wipe(msg: DatabaseWipe) -> DatabaseWipeResponse:
    # TODO: use translations
    if True:  # TODO: remove
        await confirm_action(
            "warning_database_wipe",
            "Database wipe",
            description="Do you really want to wipe the database?",
        )

    cache.wipe()

    async with StorageDatabaseContext() as database_context:
        signature = database_context.wipe()
        identifier = database_context.identifier

    return DatabaseWipeResponse(identifier=identifier, signature=signature)
