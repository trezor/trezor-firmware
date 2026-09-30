from trezorward import WardError  # noqa: F401


class WardStore:
    """Records of one app in one passphrase wallet.

    Obtain it via `apps.ward.with_ward` or `apps.ward.open_ward`. Replacing
    or deleting a record always requires an explicit approval from the user.
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

    async def set(self, key: bytes, value: bytes, description: str) -> None:
        """Store `value` under `key`.

        If a different value is already stored, the user is asked to approve
        the replacement first. `description` describes the record to the user.
        """
        raise NotImplementedError

    async def delete(self, key: bytes, description: str) -> bool:
        """Delete the record stored under `key`, return whether there was one.

        The user is asked to approve the deletion first. `description`
        describes the record to the user.
        """
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
