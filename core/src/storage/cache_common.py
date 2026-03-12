from micropython import const
from typing import TYPE_CHECKING

from trezor import utils

if utils.USE_THP:
    # Cache keys for THP
    from storage.cache_thp_keys import *  # noqa F401, F403

else:
    # Cache keys for Codec
    from storage.cache_codec_keys import *  # noqa F401, F403


# Keys that are valid across sessions
SESSIONLESS_FLAG = const(128)
APP_COMMON_SEED_WITHOUT_PASSPHRASE = const(0 | SESSIONLESS_FLAG)
APP_COMMON_SAFETY_CHECKS_TEMPORARY = const(1 | SESSIONLESS_FLAG)
APP_COMMON_REQUEST_PIN_LAST_UNLOCK = const(2 | SESSIONLESS_FLAG)
APP_COMMON_BUSY_DEADLINE_MS = const(3 | SESSIONLESS_FLAG)
APP_MISC_COSI_NONCE = const(4 | SESSIONLESS_FLAG)
APP_MISC_COSI_COMMITMENT = const(5 | SESSIONLESS_FLAG)
APP_RECOVERY_REPEATED_BACKUP_UNLOCKED = const(6 | SESSIONLESS_FLAG)

CACHE_ENCRYPTED_KEYS_SEEDLESS = (APP_COMMON_SEED_WITHOUT_PASSPHRASE,)


if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from trezorcrypto import chacha20poly1305
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

    def check_key(self, key: int) -> None:
        utils.ensure(key < len(self.fields))

    def get(self, key: int, default: T | None = None) -> bytes | T | None:  # noqa: F811
        self.check_key(key)
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
        self.check_key(key)
        return self.data[key][0] == 1

    def set(self, key: int, value: AnyBytes) -> None:
        self.check_key(key)
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
        self.check_key(key)
        # `arr[:]` allocates a slice to prevent memory fragmentation.
        self.data[key][:] = b"\x00"

    def clear(self) -> None:
        for i in range(len(self.fields)):
            self.delete(i)

    def _get_length(self, key: int) -> int:
        self.check_key(key)
        return self.fields[key]


class EncryptableDataCache(DataCache):
    """
    A DataCache that supports encryption and decryption of its fields.
    """

    def __init__(self) -> None:
        super().__init__()

    def encrypt(self, cipher_ctx: chacha20poly1305) -> None:
        if self.is_empty():
            return

        for field in self.fields_to_encrypt():
            value = self.get(field)
            if value is not None:
                self.set(field, cipher_ctx.encrypt(value))

    def decrypt(self, cipher_ctx: chacha20poly1305) -> None:
        if self.is_empty():
            return

        for field in self.fields_to_encrypt():
            value = self.get(field)
            if value is not None:
                self.set(field, cipher_ctx.decrypt(value))

    def is_preauthorized(self) -> bool:
        """
        Checks if the cache is set to preauthorization.
        """
        raise NotImplementedError("is_preauthorized must be implemented by subclasses")

    def fields_to_encrypt(self) -> Sequence[int]:
        """
        Returns a sequence of field indices that should be encrypted.
        """
        raise NotImplementedError("fields_to_encrypt must be implemented by subclasses")

    def is_empty(self) -> bool:
        """
        Checks if the session has no data set for the fields to encrypt.
        """
        for field in self.fields_to_encrypt():
            if self.get(field):
                return False
        return True


class SessionlessCache(EncryptableDataCache):
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

    def _get_length(self, key: int) -> int:
        return super()._get_length(key & ~SESSIONLESS_FLAG)

    def fields_to_encrypt(self) -> Sequence[int]:
        return CACHE_ENCRYPTED_KEYS_SEEDLESS

    def is_preauthorized(self) -> bool:
        # Sessionless cache cannot be preauthorized.
        return False
