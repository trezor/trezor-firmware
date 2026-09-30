from trezorward import WardError  # noqa: F401


class WardStore:
    """Records of one app in one passphrase wallet.

    Obtain it via `apps.ward.with_ward` or `apps.ward.open_ward`. A record may
    only be replaced or deleted with an explicit approval from the user, which
    the caller must obtain first.
    """

    def __init__(self, wallet_id: bytes, app: bytes) -> None:
        self._wallet_id = wallet_id
        self._app = app

    def subscope(self, name: bytes) -> "WardStore":
        """Return the store of the subscope `name`, e.g. a coin or a network.

        A subscope is a separate namespace, records of a store and of its
        subscopes are never visible to each other.
        """
        raise NotImplementedError

    async def get(self, key: bytes) -> bytes | None:
        """Return the value stored under `key`, or None if there is none."""
        raise NotImplementedError

    def entries(self) -> "WardIterator":
        """Iterate over all `(key, value)` records with `async for`, one at a time.

        The order of the records is unspecified. While iterating, only reading
        is allowed: modifying any WARD store in the meantime has undefined
        results (in debug builds, the iteration fails with RuntimeError).
        Once exhausted, the iterator stays exhausted.
        """
        raise NotImplementedError

    async def set(self, key: bytes, value: bytes) -> None:
        """Store `value` under `key`, replacing the current value, if any."""
        raise NotImplementedError

    async def delete(self, key: bytes) -> bool:
        """Delete the record stored under `key`, return whether there was one."""
        raise NotImplementedError


class WardIterator:
    """Iterator over the records of a store, see `WardStore.entries`."""

    def __init__(self, wallet_id: bytes, app: bytes) -> None:
        self._wallet_id = wallet_id
        self._app = app
        self._cursor = 0

    def __aiter__(self) -> "WardIterator":
        return self

    async def __anext__(self) -> tuple[bytes, bytes]:
        raise NotImplementedError
