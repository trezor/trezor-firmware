from apps.common.keychain import get_keychain
from apps.common.paths import AlwaysMatchingSchema

from .database_context import DatabaseContext
from .storage import (
    get_identifier,
    get_revision_number,
    set_identifier,
    set_revision_number,
)

# TODO: define path
path = []


class StorageDatabaseContext:
    async def __aenter__(self) -> DatabaseContext:
        self.database_context = DatabaseContext(
            get_identifier(), get_revision_number(), await get_signing_key()
        )
        return self.database_context

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        assert self.database_context.identifier is not None
        set_identifier(self.database_context.identifier)

        assert self.database_context.revision_number is not None
        set_revision_number(self.database_context.revision_number)


async def get_signing_key() -> bytes:
    keychain = await get_keychain("secp256k1", [AlwaysMatchingSchema])
    return keychain.derive(path).private_key()
