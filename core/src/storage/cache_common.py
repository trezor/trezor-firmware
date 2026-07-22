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


def _get_slip21_key(path: Sequence[bytes], seed: bytes) -> bytes:
    from trezorcrypto import hmac

    data = hmac(hmac.SHA512, b"Symmetric key seed", seed).digest()
    for label in path:
        h = hmac(hmac.SHA512, data[0:32], b"\x00")
        h.update(label)
        data = h.digest()
    return data[32:64]


class EncryptableDataCache(DataCache):
    """
    A DataCache that supports encryption and decryption of its fields.
    """

    def __init__(self) -> None:
        super().__init__()
        self.authentication_tag: bytes | None = None
        self.nonce: bytes | None = None
        self.is_encrypted: bool = False

    @staticmethod
    def _get_cache_encryption_key() -> bytes:
        """
        Returns the seed encryption key for a given session ID.
        The key is derived from the device secret and the session ID.
        """
        from storage.device import get_device_secret

        device_secret = get_device_secret()
        path = [b"TREZOR", b"STORAGE", b"CACHE", b"encryption_key"]
        return _get_slip21_key(path, device_secret)

    def clear(self) -> None:
        super().clear()
        self.authentication_tag = None
        self.nonce = None
        self.is_encrypted = False

    def encrypt(self) -> None:
        """
        Encrypts seeds in all the cached sessions and the sessionless cache.
        """
        from trezorcrypto import chacha20poly1305_encrypt, random

        if self.is_encrypted or self.is_empty() or self.is_preauthorized():
            return

        if self.nonce is not None:
            raise RuntimeError  # nonce must be unset before encrypt
        if self.authentication_tag is not None:
            raise RuntimeError  # tag must be unset before encrypt

        encryption_key = self._get_cache_encryption_key()
        self.nonce = random.bytes(12)
        cipher = chacha20poly1305_encrypt(encryption_key, self.nonce)

        for field in self.fields_to_encrypt():
            value = self.get(field)
            if value is not None:
                self.set(field, cipher.encrypt(value))
        self.authentication_tag = cipher.finish()
        self.is_encrypted = True

    def decrypt(self) -> None:
        """
        Decrypts seeds in all the cached sessions and the sessionless cache.
        """
        from trezorcrypto import chacha20poly1305_decrypt

        if not self.is_encrypted:
            return
        if self.nonce is None:
            raise RuntimeError  # nonce must be set before decrypt
        if self.authentication_tag is None:
            raise RuntimeError  # tag must be set before decrypt
        encryption_key = self._get_cache_encryption_key()
        cipher = chacha20poly1305_decrypt(encryption_key, self.nonce)

        decrypted_fields = {}
        for field in self.fields_to_encrypt():
            value = self.get(field)
            if value is not None:
                decrypted_fields[field] = cipher.decrypt(value)
        cipher.finish(self.authentication_tag)
        for field, value in decrypted_fields.items():
            self.set(field, value)
        self.is_encrypted = False
        self.nonce = None
        self.authentication_tag = None

    def is_preauthorized(self) -> bool:
        """
        Checks if the cache is set to preauthorization.
        """
        raise NotImplementedError  # is_preauthorized must be implemented by subclasses

    def fields_to_encrypt(self) -> Sequence[int]:
        """
        Returns a sequence of field indices that should be encrypted.
        """
        raise NotImplementedError  # fields_to_encrypt must be implemented by subclasses

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

    def _get_length(self, key: int) -> int:
        return super()._get_length(key & ~SESSIONLESS_FLAG)

    def fields_to_encrypt(self) -> Sequence[int]:
        return CACHE_ENCRYPTED_KEYS_SEEDLESS

    def is_preauthorized(self) -> bool:
        # Sessionless cache cannot be preauthorized.
        return False
