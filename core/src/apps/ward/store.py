from trezorward import WardError  # noqa: F401


class WardStore:
    """Records of one app in one passphrase wallet.

    Obtain it via `apps.ward.with_ward` or `apps.ward.open_ward`. A record may
    only be replaced or deleted with an explicit approval from the user, which
    the caller must obtain first.
    """

    def __init__(self, wallet_id: bytes, app: int) -> None:
        self._wallet_id = wallet_id
        self._app = app

    async def get(self, key: bytes) -> bytes | None:
        """Return the value stored under `key`, or None if there is none."""
        raise NotImplementedError

    def entries(self) -> "WardIterator":
        """Iterate over all `(key, value)` records, one record at a time."""
        raise NotImplementedError

    async def set(self, key: bytes, value: bytes) -> None:
        """Store `value` under `key`, replacing the current value, if any."""
        raise NotImplementedError

    async def delete(self, key: bytes) -> bool:
        """Delete the record stored under `key`, return whether there was one."""
        raise NotImplementedError


class WardIterator:
    def __init__(self, wallet_id: bytes, app: int) -> None:
        self._wallet_id = wallet_id
        self._app = app
        self._cursor = 0

    def __iter__(self) -> "WardIterator":
        return self

    def __next__(self) -> tuple[bytes, bytes]:
        raise NotImplementedError
