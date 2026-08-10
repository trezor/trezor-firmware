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

# Order and membership are part of the ciphertext layout -- see `EncryptableDataCache`.
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
        # Bounds only, deliberately not `check_key`: membership is not secret -- it is the
        # ciphertext layout -- so this stays answerable while encrypted.
        utils.ensure(key < len(self.fields))
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
        # Bounds only, deliberately not `check_key`: field sizes are constants.
        utils.ensure(key < len(self.fields))
        return self.fields[key]


def _get_slip21_key(path: Sequence[bytes], seed: bytes) -> bytes:
    from trezorcrypto import hmac

    data = hmac(hmac.SHA512, b"Symmetric key seed", seed).digest()
    for label in path:
        h = hmac(hmac.SHA512, data[0:32], b"\x00")
        h.update(label)
        data = h.digest()
    return data[32:64]


# ChaCha20-Poly1305 nonce and authentication tag sizes.
_NONCE_LENGTH = const(12)
_TAG_LENGTH = const(16)


class EncryptableDataCache(DataCache):
    """
    A DataCache whose sensitive fields are encrypted while the device is locked.

    The fields listed by `fields_to_encrypt()` that are *set* are encrypted together as
    one ChaCha20-Poly1305 stream, with a single nonce and tag. Unset fields are skipped,
    so which fields are set, and their order, are part of the ciphertext layout: decrypt
    must consume the keystream in the same order and lengths or the tag check fails.
    `check_key` keeps that set stable by refusing writes and deletes while encrypted.
    """

    def __init__(self) -> None:
        super().__init__()
        self.nonce = bytearray(_NONCE_LENGTH)
        self.authentication_tag = bytearray(_TAG_LENGTH)
        self.is_encrypted: bool = False
        self.was_preauthorized: bool = False

    @staticmethod
    def _get_cache_encryption_key() -> bytes:
        """
        Returns the cache encryption key, derived from the device secret.

        The path is constant, so this is one key for every cache and every lock cycle --
        keystream separation comes from the per-cache random nonce, not from the key.
        """
        from storage.device import get_device_secret

        device_secret = get_device_secret()
        path = [b"TREZOR", b"STORAGE", b"CACHE", b"encryption_key"]
        return _get_slip21_key(path, device_secret)

    def check_key(self, key: int) -> None:
        """
        Do not allow access to an encrypted field's *value*. Reading one would hand out
        ciphertext; writing or deleting one would shift the shared keystream and break
        every field after it, so the whole cache would fail to decrypt. `is_set` and
        `_get_length` bypass this on purpose -- neither touches the value.
        """
        super().check_key(key)
        if self.is_encrypted and self._is_encrypted_field(key):
            raise RuntimeError  # encrypted fields are inaccessible while locked

    def _is_encrypted_field(self, key: int) -> bool:
        return key in self.fields_to_encrypt()

    def clear(self) -> None:
        # `is_encrypted` must come first: `delete` refuses encrypted fields,
        # so the other order would raise on the first encrypted field.
        self.is_encrypted = False
        super().clear()
        # Zero in place to keep the preallocated buffers
        self.nonce[:] = bytes(_NONCE_LENGTH)
        self.authentication_tag[:] = bytes(_TAG_LENGTH)
        self.was_preauthorized = False

    def encrypt(self) -> None:
        """
        Encrypts this cache's set encrypted fields into one ChaCha20-Poly1305 stream.

        No-op if there is nothing to protect, or if the plaintext is deliberate
        (preauthorized). Any failure is fatal -- `storage.cache.encrypt_cache` halts on it.
        """
        from trezorcrypto import chacha20poly1305_encrypt, random

        if self.is_encrypted or not self.has_secrets():
            return
        if self.is_preauthorized():
            # Plaintext secrets are deliberate here; remember that, so the invariant
            # check can tell this apart from a lock path that skipped encryption.
            self.was_preauthorized = True
            return


        # An unused nonce/tag is erased (all-zero), so a live one here means a previous
        # encrypt or decrypt died part-way. Re-encrypting over it would double-encrypt the
        # fields already done, and that stream is self-consistent -- the tag would verify
        # on unlock and `get` would return garbage as a seed, with no error anywhere.
        if any(self.nonce) or any(self.authentication_tag):
            raise RuntimeError  # nonce and tag must be erased before encrypt

        encryption_key = self._get_cache_encryption_key()
        self.nonce[:] = random.bytes(_NONCE_LENGTH)
        cipher = chacha20poly1305_encrypt(encryption_key, self.nonce)

        for field in self.fields_to_encrypt():
            value = self.get(field)
            if value is not None:
                # ChaCha20 is a stream cipher and the tag is kept outside the field, so
                # the ciphertext is the same length as the plaintext and fits back in.
                self.set(field, cipher.encrypt(value))
        self.authentication_tag[:] = cipher.finish()
        self.is_encrypted = True

    def decrypt(self) -> None:
        """
        Decrypts this cache's fields, verifying the authentication tag.

        Any failure is fatal -- `storage.cache.decrypt_cache` halts on it.
        """
        from trezorcrypto import chacha20poly1305_decrypt

        self.was_preauthorized = False  # plaintext secrets are no longer deliberate
        if not self.is_encrypted:
            return

        # Symmetric to `encrypt`: a live (non-zero) nonce and tag must be present
        # whenever `is_encrypted` is set.
        if not any(self.nonce) or not any(self.authentication_tag):
            raise RuntimeError  # nonce and tag must be set before decrypt

        encryption_key = self._get_cache_encryption_key()
        cipher = chacha20poly1305_decrypt(encryption_key, self.nonce)

        # The cache is not decrypted yet, but this lifts the restriction on accessing
        # (`self.get()`) encrypted fields so that they can be decrypted in the next step.
        self.is_encrypted = False
        decrypted_fields = {}
        for field in self.fields_to_encrypt():
            value = self.get(field)
            if value is not None:
                decrypted_fields[field] = cipher.decrypt(value)
        cipher.finish(self.authentication_tag)
        for field, value in decrypted_fields.items():
            self.set(field, value)
        # Erase the now-spent nonce and tag; zero in place to keep the buffers.
        self.nonce[:] = bytes(_NONCE_LENGTH)
        self.authentication_tag[:] = bytes(_TAG_LENGTH)

    def is_preauthorized(self) -> bool:
        """
        Checks if the cache is set to preauthorization.
        """
        raise NotImplementedError  # is_preauthorized must be implemented by subclasses

    def fields_to_encrypt(self) -> Sequence[int]:
        """
        Returns the field indices to encrypt. Order and membership are part of the
        ciphertext layout -- changing either is a format change, not a refactor.
        """
        raise NotImplementedError  # fields_to_encrypt must be implemented by subclasses

    def has_secrets(self) -> bool:
        """Checks if any field that needs encrypting is set."""
        for field in self.fields_to_encrypt():
            if self.is_set(field):
                return True
        return False


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

    def _is_encrypted_field(self, key: int) -> bool:
        return super()._is_encrypted_field(key | SESSIONLESS_FLAG)

    def is_preauthorized(self) -> bool:
        # Sessionless cache cannot be preauthorized.
        return False
