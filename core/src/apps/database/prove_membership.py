from typing import TYPE_CHECKING

from trezor.database.storage_database_context import StorageDatabaseContext
from trezor.messages import Success

if TYPE_CHECKING:
    from trezor.messages import DatabaseProveMembership

from trezor.database import cache


async def prove_membership(msg: DatabaseProveMembership) -> Success:
    assert msg.database_time is not None
    assert msg.database_signature is not None
    assert msg.key is not None
    assert msg.proof is not None

    async with StorageDatabaseContext() as database_context:
        value = database_context.verify_membership(
            msg.database_time,
            msg.database_signature,
            msg.key,
            msg.proof,
        )
        cache.set(msg.key, value)

    return Success()
