import trezorward
from trezorward import WardError  # noqa: F401

if __debug__:
    # Number of modifications of any store, lets debug builds detect
    # modifications during iteration.
    _modifications = 0


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
        if len(name) > 0xFF:
            raise ValueError("Subscope name too long")
        # length-prefixed, so that different subscopes never share an identifier
        return WardStore(self._wallet_id, self._app + bytes([len(name)]) + name)

    async def get(self, key: bytes) -> bytes | None:
        """Return the value stored under `key`, or None if there is none."""
        return trezorward.get(self._wallet_id, self._app, key)

    def entries(self) -> "WardIterator":
        """Iterate over all `(key, value)` records with `async for`, one at a time.

        The order of the records is unspecified. While iterating, only reading
        is allowed: modifying any WARD store in the meantime has undefined
        results (in debug builds, the iteration fails with RuntimeError).
        Once exhausted, the iterator stays exhausted.
        """
        return WardIterator(self._wallet_id, self._app)

    async def set(self, key: bytes, value: bytes) -> None:
        """Store `value` under `key`, replacing the current value, if any."""
        if __debug__:
            global _modifications
            _modifications += 1
        trezorward.set(self._wallet_id, self._app, key, value)

    async def delete(self, key: bytes) -> bool:
        """Delete the record stored under `key`, return whether there was one."""
        if __debug__:
            global _modifications
            _modifications += 1
        return trezorward.delete(self._wallet_id, self._app, key)


class WardIterator:
    """Iterator over the records of a store, see `WardStore.entries`."""

    def __init__(self, wallet_id: bytes, app: bytes) -> None:
        self._wallet_id = wallet_id
        self._app = app
        self._cursor: int | None = 0  # None once exhausted
        if __debug__:
            self._modifications = _modifications

    def __aiter__(self) -> "WardIterator":
        return self

    async def __anext__(self) -> tuple[bytes, bytes]:
        if self._cursor is None:
            raise StopAsyncIteration
        if __debug__:
            if self._modifications != _modifications:
                raise RuntimeError("WARD modified during iteration")
        entry = trezorward.next_entry(self._wallet_id, self._app, self._cursor)
        if entry is None:
            self._cursor = None
            raise StopAsyncIteration
        self._cursor, key, value = entry
        return key, value
