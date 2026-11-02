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

# Encrypted fields come first, as in the Codec and THP keys.
CACHE_ENCRYPTED_COUNT_SESSIONLESS = const(1)


if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from collections.abc import Sequence
    from typing import TypeVar, overload

    T = TypeVar("T")

# ChaCha20-Poly1305 nonce and authentication tag sizes.
_NONCE_LENGTH = const(12)
_TAG_LENGTH = const(16)


class InvalidSessionError(Exception):
    pass


def get_cache_encryption_key() -> bytes:
    """
    Returns the cache encryption key, derived from the device secret.
    """
    from storage.device import get_device_secret
    from trezor.crypto.slip21 import Slip21Node

    device_secret = get_device_secret()
    path = [b"TREZOR", b"Storage cache encryption key"]
    node = Slip21Node(device_secret)
    node.derive_path(path)
    return node.key()


class DataCache:
    """
    A single unit of cache storage, designed to store common-type
    values efficiently in one preallocated bytearray.

    Its sensitive fields are encrypted while the device is locked.
    Field values sit back to back in `data`. The first `encrypted_count` fields, set or
    not, are encrypted as one ChaCha20-Poly1305 region with a single nonce and tag.
    Their `value_lengths` stay in plaintext, so `is_set` works while locked.
    The tag authenticates them too.
    """

    field_sizes: Sequence[int]
    encrypted_count: int  # fields below this index are encrypted while locked

    def __init__(self) -> None:
        # field_sizes must be defined in the subclass before calling super().__init__()
        self.data = bytearray(sum(self.field_sizes))
        # 0 if unset, else length + 1
        self.value_lengths = bytearray(len(self.field_sizes))
        assert max(self.field_sizes) < 255  # value_lengths stores length + 1 in a byte
        self.nonce = bytearray(_NONCE_LENGTH)
        self.authentication_tag = bytearray(_TAG_LENGTH)
        self.is_encrypted: bool = False
        if __debug__:
            self.was_preauthorized: bool = False

    if TYPE_CHECKING:

        @overload
        def get(self, key: int) -> bytes | None:  # noqa: F811
            ...

        @overload
        def get(self, key: int, default: T) -> bytes | T:  # noqa: F811
            ...

    def check_key(self, key: int) -> None:
        """
        Do not allow access to an encrypted field's *value*. Writing or deleting one
        would corrupt the ciphertext and fail the decryption authenticity check.
        """
        utils.ensure(key < len(self.field_sizes))
        if self.is_encrypted and key < self.encrypted_count:
            raise RuntimeError  # encrypted fields are inaccessible while locked

    def get(self, key: int, default: T | None = None) -> bytes | T | None:  # noqa: F811
        self.check_key(key)
        length = self.value_lengths[key]
        if length == 0:
            return default
        start = self._field_start(key)
        return bytes(self.data[start : start + length - 1])

    def get_bool(self, key: int) -> bool:  # noqa: F811
        return self.get(key) is not None

    def get_int(self, key: int, default: T | None = None) -> int | T | None:  # noqa: F811
        encoded = self.get(key)
        if encoded is None:
            return default
        else:
            return int.from_bytes(encoded, "big")

    def is_set(self, key: int) -> bool:
        utils.ensure(key < len(self.field_sizes))
        return self.value_lengths[key] != 0

    def set(self, key: int, value: AnyBytes) -> None:
        self.check_key(key)
        size = self.field_sizes[key]
        utils.ensure(len(value) <= size)
        start = self._field_start(key)
        end = start + len(value)
        if len(value) < size:
            # zero the rest of the field
            self.data[end : start + size] = bytes(size - len(value))
        self.data[start:end] = value
        self.value_lengths[key] = len(value) + 1

    def set_bool(self, key: int, value: bool) -> None:
        assert self._get_field_size(key) == 0  # skipped in production build
        if value:
            self.set(key, b"")
        else:
            self.delete(key)

    def set_int(self, key: int, value: int) -> None:
        length = self._get_field_size(key)
        encoded = value.to_bytes(length, "big")
        assert int.from_bytes(encoded, "big") == value

        self.set(key, encoded)

    def delete(self, key: int) -> None:
        self.check_key(key)
        start = self._field_start(key)
        self.data[start : start + self.field_sizes[key]] = bytes(self.field_sizes[key])
        self.value_lengths[key] = 0

    def clear(self) -> None:
        self.is_encrypted = False
        # memzero does not allocate
        utils.memzero(self.data)
        utils.memzero(self.value_lengths)
        utils.memzero(self.nonce)
        utils.memzero(self.authentication_tag)
        if __debug__:
            self.was_preauthorized = False

    def _get_field_size(self, key: int) -> int:
        utils.ensure(key < len(self.field_sizes))
        return self.field_sizes[key]

    def _field_start(self, key: int) -> int:
        start = 0
        for i in range(key):
            start += self.field_sizes[i]
        return start

    def encrypt(self, encryption_key: bytes) -> None:
        """
        Encrypts this cache's secret fields using one ChaCha20-Poly1305 stream.
        Does nothing if there is nothing to protect, or if the session is preauthorized.
        """
        from trezorcrypto import chacha20poly1305_encrypt, random

        if self.is_encrypted or not self.has_secrets():
            return
        if self.is_preauthorized():
            if __debug__:
                self.was_preauthorized = True
            return

        if any(self.nonce) or any(self.authentication_tag):
            raise RuntimeError  # nonce and tag must be erased before encrypt

        self.nonce[:] = random.bytes(_NONCE_LENGTH)
        cipher = chacha20poly1305_encrypt(encryption_key, self.nonce)

        end = self._field_start(self.encrypted_count)
        cipher.auth(memoryview(self.value_lengths)[: self.encrypted_count])
        ciphertext = cipher.encrypt(memoryview(self.data)[:end])
        self.authentication_tag[:] = cipher.finish()
        self.data[:end] = ciphertext
        self.is_encrypted = True

    def decrypt(self, encryption_key: bytes) -> None:
        """
        Decrypts this cache's fields, verifying the authentication tag.
        """
        from trezorcrypto import chacha20poly1305_decrypt

        if __debug__:
            self.was_preauthorized = False  # plaintext secrets are no longer deliberate
        if not self.is_encrypted:
            return

        if not any(self.nonce) or not any(self.authentication_tag):
            raise RuntimeError  # nonce and tag must be set before decrypt

        cipher = chacha20poly1305_decrypt(encryption_key, self.nonce)
        end = self._field_start(self.encrypted_count)
        cipher.auth(memoryview(self.value_lengths)[: self.encrypted_count])
        plaintext = cipher.decrypt(memoryview(self.data)[:end])
        cipher.finish(self.authentication_tag)  # raises before anything is written back
        self.data[:end] = plaintext
        self.is_encrypted = False
        # Erase the now-spent nonce and tag
        utils.memzero(self.nonce)
        utils.memzero(self.authentication_tag)

    def is_preauthorized(self) -> bool:
        """
        Checks if the cache is set to preauthorization.
        """
        raise NotImplementedError  # is_preauthorized must be implemented by subclasses

    def has_secrets(self) -> bool:
        """Checks if any field that needs encrypting is set."""
        for field in range(self.encrypted_count):
            if self.is_set(field):
                return True
        return False


class SessionlessCache(DataCache):
    """
    A cache for values that are independent of both
    passphrase seed derivation and the active session.
    """

    encrypted_count = CACHE_ENCRYPTED_COUNT_SESSIONLESS

    def __init__(self) -> None:
        self.field_sizes = (
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

    def _get_field_size(self, key: int) -> int:
        return super()._get_field_size(key & ~SESSIONLESS_FLAG)

    def _field_start(self, key: int) -> int:
        return super()._field_start(key & ~SESSIONLESS_FLAG)

    def is_preauthorized(self) -> bool:
        # Sessionless cache cannot be preauthorized.
        return False
