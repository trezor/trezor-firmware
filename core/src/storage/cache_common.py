from micropython import const
from typing import TYPE_CHECKING

from trezor import utils

if utils.USE_THP:
    # Cache keys for THP
    from .cache_thp_keys import *  # noqa F401, F403

else:
    # Cache keys for Codec
    from .cache_codec_keys import *  # noqa F401, F403


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
    from buffer_types import AnyBytes
    from collections.abc import Sequence
    from trezorcrypto import SecretOwner, secbytes
    from typing import TypeVar, overload

    T = TypeVar("T")


class InvalidSessionError(Exception):
    pass


class DataCache:
    """
    A single unit of cache storage, designed to store common-type
    values efficiently in bytearrays in a sequential manner.
    """

    fields: Sequence[int]  # field sizes
    secret_fields: tuple[int, ...] = ()
    sessionless = False

    def __init__(self) -> None:
        from trezorcrypto import SecretOwner, secbytes

        # Reuse main's slot positions and capacities. A secret holder replaces
        # its plaintext bytearray; values change in place across loop restarts.
        self._secret_owner = SecretOwner(None, False)
        self.data = [
            secbytes(None, size) if key in self.secret_fields else bytearray(size + 1)
            for key, size in enumerate(self.fields)
        ]
        if APP_COMMON_SEED_WITHOUT_PASSPHRASE in self.secret_fields:
            # Partition the existing no-passphrase cache by owner: another
            # session cannot open this owner's record. Sessionless requests
            # use the original sessionless slot instead of this extra slot.
            self.data.append(secbytes(None, 64))

    def get_secret_owner(self) -> SecretOwner:
        owner = self._secret_owner
        if not owner.valid():
            self._destroy_secrets()
            owner.renew()
        return owner

    def _destroy_secrets(self) -> None:
        from trezorcrypto import secbytes

        for value in self.data:
            if isinstance(value, secbytes):
                value.destroy()

    def _secret_index(self, key: int) -> int:
        index = key & ~SESSIONLESS_FLAG if self.sessionless else key
        utils.ensure(index in self.secret_fields)
        return (
            len(self.fields) if index == APP_COMMON_SEED_WITHOUT_PASSPHRASE else index
        )

    def get_secret(self, key: int) -> secbytes | None:
        from trezorcrypto import secbytes

        self.get_secret_owner()
        value = self.data[self._secret_index(key)]
        assert isinstance(value, secbytes)
        return None if value.empty() else value

    def take_secret(self, key: int, value: secbytes) -> None:
        from trezorcrypto import retain_secret, secbytes

        owner = self.get_secret_owner()
        holder = self.data[self._secret_index(key)]
        assert isinstance(holder, secbytes)
        if holder is value:
            return
        retain_secret(value, owner)
        holder.take(value)

    def delete_secret(self, key: int) -> None:
        from trezorcrypto import secbytes

        value = self.data[self._secret_index(key)]
        assert isinstance(value, secbytes)
        value.destroy()

    def _public_slot(self, key: int) -> bytearray:
        utils.ensure(key < len(self.fields))
        value = self.data[key]
        if not isinstance(value, bytearray):
            raise TypeError("Use the secret cache interface")
        return value

    if TYPE_CHECKING:

        @overload
        def get(self, key: int) -> bytes | None:  # noqa: F811
            ...

        @overload
        def get(self, key: int, default: T) -> bytes | T:  # noqa: F811
            ...

    def get(self, key: int, default: T | None = None) -> bytes | T | None:  # noqa: F811
        value = self._public_slot(key)
        if value[0] != 1:
            return default
        return bytes(value[1:])

    def get_bool(self, key: int) -> bool:  # noqa: F811
        return self.get(key) is not None

    def get_int(self, key: int, default: T | None = None) -> int | T | None:  # noqa: F811
        encoded = self.get(key)
        if encoded is None:
            return default
        else:
            return int.from_bytes(encoded, "big")

    def is_set(self, key: int) -> bool:
        from trezorcrypto import secbytes

        utils.ensure(key < len(self.fields))
        value = self.data[key]
        if isinstance(value, secbytes):
            self.get_secret_owner()
            return not value.empty()
        return value[0] == 1

    def set(self, key: int, value: AnyBytes) -> None:
        slot = self._public_slot(key)
        utils.ensure(len(value) <= self.fields[key])
        slot[0] = 1
        slot[1:] = value

    def set_bool(self, key: int, value: bool) -> None:
        assert self._get_length(key) == 0  # skipping get_length in production build
        if value:
            self.set(key, b"")
        else:
            self.delete(key)

    def set_int(self, key: int, value: int) -> None:
        length = self._get_length(key)
        encoded = value.to_bytes(length, "big")
        assert int.from_bytes(encoded, "big") == value

        self.set(key, encoded)

    def delete(self, key: int) -> None:
        from trezorcrypto import secbytes

        utils.ensure(key < len(self.fields))
        value = self.data[key]
        if isinstance(value, secbytes):
            value.destroy()
        else:
            # `arr[:]` allocates a slice to prevent memory fragmentation.
            value[:] = b"\x00"

    def clear(self) -> None:
        # Revoke before an allocation or callback can interrupt clearing.
        self._secret_owner.destroy()
        self._destroy_secrets()
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

    sessionless = True
    secret_fields = (APP_COMMON_SEED_WITHOUT_PASSPHRASE & ~SESSIONLESS_FLAG,)

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

    def get_int(self, key: int, default: T | None = None) -> int | T | None:  # noqa: F811
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
        super().clear()
