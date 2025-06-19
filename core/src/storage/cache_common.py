from micropython import const
from typing import TYPE_CHECKING

from trezor import utils

# Traditional cache keys
APP_COMMON_SEED = const(0)
APP_COMMON_AUTHORIZATION_TYPE = const(1)
APP_COMMON_AUTHORIZATION_DATA = const(2)
APP_COMMON_NONCE = const(3)
if not utils.BITCOIN_ONLY:
    APP_COMMON_DERIVE_CARDANO = const(4)
    APP_CARDANO_ICARUS_SECRET = const(5)
    APP_CARDANO_ICARUS_TREZOR_SECRET = const(6)
    APP_MONERO_LIVE_REFRESH = const(7)

# Keys that are valid across sessions
SESSIONLESS_FLAG = const(128)
APP_COMMON_SEED_WITHOUT_PASSPHRASE = const(0 | SESSIONLESS_FLAG)
APP_COMMON_SAFETY_CHECKS_TEMPORARY = const(1 | SESSIONLESS_FLAG)
APP_COMMON_REQUEST_PIN_LAST_UNLOCK = const(2 | SESSIONLESS_FLAG)
APP_COMMON_BUSY_DEADLINE_MS = const(3 | SESSIONLESS_FLAG)
APP_MISC_COSI_NONCE = const(4 | SESSIONLESS_FLAG)
APP_MISC_COSI_COMMITMENT = const(5 | SESSIONLESS_FLAG)
APP_RECOVERY_REPEATED_BACKUP_UNLOCKED = const(6 | SESSIONLESS_FLAG)


if TYPE_CHECKING:
    from typing import Sequence, TypeVar, overload

    T = TypeVar("T")


class InvalidSessionError(Exception):
    pass


class DataCache:
    """
    A single unit of cache storage, designed to store common-type
    values efficiently in bytearrays in a sequential manner.
    """

    fields: Sequence[int]  # field sizes

    def __init__(self) -> None:
        self.data = [bytearray(f + 1) for f in self.fields]

    if TYPE_CHECKING:

        @overload
        def get(self, key: int) -> bytes | None:  # noqa: F811
            ...

        @overload
        def get(self, key: int, default: T) -> bytes | T:  # noqa: F811
            ...

    def get(self, key: int, default: T | None = None) -> bytes | T | None:  # noqa: F811
        utils.ensure(key < len(self.fields))
        if self.data[key][0] != 1:
            return default
        return bytes(self.data[key][1:])

    def get_bool(self, key: int) -> bool:  # noqa: F811
        return self.get(key) is not None

    def get_int(
        self, key: int, default: T | None = None
    ) -> int | T | None:  # noqa: F811
        encoded = self.get(key)
        if encoded is None:
            return default
        else:
            return int.from_bytes(encoded, "big")

    def is_set(self, key: int) -> bool:
        utils.ensure(key < len(self.fields))
        return self.data[key][0] == 1

    def set(self, key: int, value: bytes) -> None:
        utils.ensure(key < len(self.fields))
        utils.ensure(len(value) <= self.fields[key])
        self.data[key][0] = 1
        self.data[key][1:] = value

    def set_bool(self, key: int, value: bool) -> None:
        assert self._get_length(key) == 0  # skipping get_length in production build
        if value:
            self.set(key, b"")
        else:
            self.delete(key)

    def set_int(self, key: int, value: int) -> None:
        length = self._get_length(key)
        encoded = value.to_bytes(length, "big")

        # Ensure that the value fits within the length. Micropython's int.to_bytes()
        # doesn't raise OverflowError.
        assert int.from_bytes(encoded, "big") == value

        self.set(key, encoded)

    def delete(self, key: int) -> None:
        utils.ensure(key < len(self.fields))
        # `arr[:]` allocates a slice to prevent memory fragmentation.
        self.data[key][:] = b"\x00"

    def clear(self) -> None:
        for i in range(len(self.fields)):
            self.delete(i)

    def _get_length(self, key: int) -> int:
        utils.ensure(key < len(self.fields))
        return self.fields[key]


class SessionlessCache(DataCache):
    """
    A cache for values that are independent of both
    passphrase seed derivation and the active session.
    """

    def __init__(self) -> None:
        self.fields = (
            64,  # APP_COMMON_SEED_WITHOUT_PASSPHRASE
            1,  # APP_COMMON_SAFETY_CHECKS_TEMPORARY
            8,  # APP_COMMON_REQUEST_PIN_LAST_UNLOCK
            8,  # APP_COMMON_BUSY_DEADLINE_MS
            32,  # APP_MISC_COSI_NONCE
            32,  # APP_MISC_COSI_COMMITMENT
            0,  # APP_RECOVERY_REPEATED_BACKUP_UNLOCKED
        )
        super().__init__()

    def get(self, key: int, default: T | None = None) -> bytes | T | None:  # noqa: F811
        return super().get(key & ~SESSIONLESS_FLAG, default)

    def get_bool(self, key: int) -> bool:  # noqa: F811
        return super().get_bool(key & ~SESSIONLESS_FLAG)

    def get_int(
        self, key: int, default: T | None = None
    ) -> int | T | None:  # noqa: F811
        return super().get_int(key & ~SESSIONLESS_FLAG, default)

    def _get_length(self, key: int) -> int:
        return super()._get_length(key & ~SESSIONLESS_FLAG)

    def is_set(self, key: int) -> bool:
        return super().is_set(key & ~SESSIONLESS_FLAG)

    def set(self, key: int, value: bytes) -> None:
        super().set(key & ~SESSIONLESS_FLAG, value)

    def set_bool(self, key: int, value: bool) -> None:
        super().set_bool(key & ~SESSIONLESS_FLAG, value)

    def set_int(self, key: int, value: int) -> None:
        super().set_int(key & ~SESSIONLESS_FLAG, value)

    def delete(self, key: int) -> None:
        super().delete(key & ~SESSIONLESS_FLAG)

    def clear(self) -> None:
        for i in range(len(self.fields)):
            self.delete(i)
