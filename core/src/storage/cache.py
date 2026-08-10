import builtins
import gc
from typing import TYPE_CHECKING

from storage.cache_common import SESSIONLESS_FLAG, SessionlessCache, EncryptableDataCache
from trezor import utils

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Sequence

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

# Built once, at import: the lock path must not allocate.
_ALL_CACHES: Sequence[EncryptableDataCache] = _PROTOCOL_CACHE._SESSIONS + [_SESSIONLESS_CACHE]

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


def get_int_all_sessions(key: int) -> builtins.set[int]:
    """
    Returns set of int values associated with a given key from all relevant sessions.

    If the key has the `SESSIONLESS_FLAG` set, the values are retrieved
    from the sessionless cache. Otherwise, the values are fetched
    from the protocol cache.

    `key` must not be an encrypted field -- `get` raises on those while locked.
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


# Either direction can leave a cache whose ciphertext reads back as plaintext: `encrypt`
# sets `is_encrypted` last, `decrypt` clears it before verifying the tag. Continuing would
# serve that to `get_seed`. The caches deliberately do not repair themselves -- halting is
# the whole mechanism, so do not narrow the `except`, and do not skip to the next cache.


def encrypt_cache() -> None:
    """
    Encrypts seeds in all the cached sessions and the sessionless cache.
    """
    for session in _ALL_CACHES:
        try:
            session.encrypt()
        except Exception as e:
            if __debug__:
                from trezor import log
                log.exception(__name__, e)
            utils.halt(e.__class__.__name__)


def decrypt_cache() -> None:
    """
    Decrypts seeds in all the cached sessions and the sessionless cache.
    """
    for session in _ALL_CACHES:
        try:
            session.decrypt()
        except Exception as e:
            if __debug__:
                from trezor import log
                log.exception(__name__, e)
            utils.halt(e.__class__.__name__)

if __debug__:

    def no_unexpected_plaintext() -> bool:
        """True if every cache that should have been encrypted was."""
        for session in _ALL_CACHES:
            if session.has_secrets() and not (
                session.is_encrypted or session.is_preauthorized() or session.was_preauthorized
            ):
                return False
        return True