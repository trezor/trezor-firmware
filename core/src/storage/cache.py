import builtins
import gc
from typing import TYPE_CHECKING, Sequence

from storage.cache_common import (
    SESSIONLESS_FLAG,
    EncryptableDataCache,
    SessionlessCache,
)
from trezor import log, utils

if TYPE_CHECKING:
    from buffer_types import AnyBytes

# Cache initialization
_SESSIONLESS_CACHE = SessionlessCache()


if utils.USE_THP:
    from storage import cache_thp

    _PROTOCOL_CACHE = cache_thp
else:
    from storage import cache_codec

    _PROTOCOL_CACHE = cache_codec

_PROTOCOL_CACHE.initialize()
_SESSIONLESS_CACHE.clear()

gc.collect()


def clear_all(excluded: tuple[AnyBytes, AnyBytes] | None = None) -> None:
    """
    Clears all data from both the protocol cache and the sessionless cache.
    """
    global autolock_last_touch
    autolock_last_touch = None
    _SESSIONLESS_CACHE.clear()

    if utils.USE_THP and excluded is not None:
        # If we want to keep THP connection alive, we do not clear communication keys
        cache_thp.clear_all_except_one_session_keys(excluded)
    else:
        _PROTOCOL_CACHE.clear_all()

    CACHE_ENCRYPTION_AUTHENTIZATION_TAG[:] = b"\x00" * len(
        CACHE_ENCRYPTION_AUTHENTIZATION_TAG
    )
    CACHE_ENCRYPTION_NONCE[:] = b"\x00" * len(CACHE_ENCRYPTION_NONCE)


def get_int_all_sessions(key: int) -> builtins.set[int]:
    """
    Returns set of int values associated with a given key from all relevant sessions.

    If the key has the `SESSIONLESS_FLAG` set, the values are retrieved
    from the sessionless cache. Otherwise, the values are fetched
    from the protocol cache.
    """
    if key & SESSIONLESS_FLAG:
        values = builtins.set()
        encoded = _SESSIONLESS_CACHE.get(key)
        if encoded is not None:
            values.add(int.from_bytes(encoded, "big"))
        return values
    return _PROTOCOL_CACHE.get_int_all_sessions(key)


def get_sessionless_cache() -> SessionlessCache:
    return _SESSIONLESS_CACHE


# === Homescreen storage ===
# This does not logically belong to the "cache" functionality, but the cache module is
# a convenient place to put this.
# When a Homescreen layout is instantiated, it checks the value of `homescreen_shown`
# to know whether it should render itself or whether the result of a previous instance
# is still on. This way we can avoid unnecessary fadeins/fadeouts when a workflow ends.
HOMESCREEN_ON = object()
LOCKSCREEN_ON = object()
BUSYSCREEN_ON = object()
homescreen_shown: object | None = None

# Timestamp of last autolock activity.
# Here to persist across main loop restart between workflows.
autolock_last_touch: int | None = None


CACHE_ENCRYPTION_NONCE = bytearray(12)
CACHE_ENCRYPTION_AUTHENTIZATION_TAG = bytearray(16)
CACHE_ENCRYPTION_AUTHENTIZATION_TAG[:] = b"\x00" * len(
    CACHE_ENCRYPTION_AUTHENTIZATION_TAG
)
CACHE_ENCRYPTION_NONCE[:] = b"\x00" * len(CACHE_ENCRYPTION_NONCE)


def _get_caches_to_encrypt() -> Sequence[EncryptableDataCache]:
    caches = _PROTOCOL_CACHE._SESSIONS + [_SESSIONLESS_CACHE]
    # if utils.USE_THP:
    #     caches += cache_thp._CHANNELS
    return [
        cache
        for cache in caches
        if not cache.is_empty() and not cache.is_preauthorized()
    ]


def _get_slip21_key(path: Sequence[bytes], seed: bytes) -> bytes:
    from trezorcrypto import hmac

    data = hmac(hmac.SHA512, b"Symmetric key seed", seed).digest()
    for label in path:
        h = hmac(hmac.SHA512, data[0:32], b"\x00")
        h.update(label)
        data = h.digest()
    return data[32:64]


def _get_cache_encryption_key() -> bytes:
    """
    Returns the seed encryption key for a given session ID.
    The key is derived from the device secret and the session ID.
    """
    from storage.device import get_device_secret

    device_secret = get_device_secret()
    label = b"Cache encryption key"
    return _get_slip21_key([label], device_secret)


def encrypt_cache() -> None:
    """
    Encrypts seeds in all the cached sessions and the sessionless cache.
    """
    from trezorcrypto import chacha20poly1305, random

    if any(CACHE_ENCRYPTION_NONCE) and any(CACHE_ENCRYPTION_AUTHENTIZATION_TAG):
        return
    if any(CACHE_ENCRYPTION_AUTHENTIZATION_TAG):
        raise ValueError("Cache encryption authentication tag is already set")
    if any(CACHE_ENCRYPTION_NONCE):
        raise ValueError("Cache encryption nonce is already set")

    log.debug(__name__, "Encrypting cache")
    caches_to_encrypt = _get_caches_to_encrypt()
    if not caches_to_encrypt:
        log.debug(__name__, "No caches to encrypt")
        return
    encryption_key = _get_cache_encryption_key()
    nonce = random.bytes(12)
    cipher = chacha20poly1305(encryption_key, nonce)
    CACHE_ENCRYPTION_NONCE[:] = nonce

    for cache in caches_to_encrypt:
        cache.encrypt(cipher)

    CACHE_ENCRYPTION_AUTHENTIZATION_TAG[:] = cipher.finish()


def decrypt_cache() -> None:
    """
    Decrypts seeds in all the cached sessions and the sessionless cache.
    """
    from trezorcrypto import chacha20poly1305

    log.debug(__name__, "Decrypting cache")
    caches_to_decrypt = _get_caches_to_encrypt()
    if not caches_to_decrypt:
        log.debug(__name__, "No caches to decrypt")
        return

    encryption_key = _get_cache_encryption_key()
    if not any(CACHE_ENCRYPTION_NONCE) and not any(CACHE_ENCRYPTION_AUTHENTIZATION_TAG):
        return
    if not any(CACHE_ENCRYPTION_NONCE):
        raise ValueError("Cache encryption nonce is empty")
    if not any(CACHE_ENCRYPTION_AUTHENTIZATION_TAG):
        raise ValueError("Cache encryption authentication tag is empty")

    cipher = chacha20poly1305(encryption_key, CACHE_ENCRYPTION_NONCE)
    for cache in caches_to_decrypt:
        cache.decrypt(cipher)

    CACHE_ENCRYPTION_NONCE[:] = b"\x00" * len(CACHE_ENCRYPTION_NONCE)
    if cipher.finish() != CACHE_ENCRYPTION_AUTHENTIZATION_TAG:
        for cache in _get_caches_to_encrypt():
            cache.clear()
        CACHE_ENCRYPTION_AUTHENTIZATION_TAG[:] = b"\x00" * len(
            CACHE_ENCRYPTION_AUTHENTIZATION_TAG
        )
        raise ValueError("Cache decryption failed: authentication tag does not match")

    CACHE_ENCRYPTION_AUTHENTIZATION_TAG[:] = b"\x00" * len(
        CACHE_ENCRYPTION_AUTHENTIZATION_TAG
    )
