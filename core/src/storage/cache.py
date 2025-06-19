import builtins
import gc

from storage import cache_codec
from storage.cache_common import SESSIONLESS_FLAG, SessionlessCache
from trezor import log

# Cache initialization
_SESSIONLESS_CACHE = SessionlessCache()
_PROTOCOL_CACHE = cache_codec
_PROTOCOL_CACHE.initialize()
_SESSIONLESS_CACHE.clear()

gc.collect()


def clear_all() -> None:
    """
    Clears all data from both the protocol cache and the sessionless cache.
    """
    global autolock_last_touch
    autolock_last_touch = None
    _SESSIONLESS_CACHE.clear()
    _PROTOCOL_CACHE.clear_all()


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


def encrypt_seeds() -> None:
    """
    Encrypts seeds in all the cached sessions and the sessionless cache.
    """
    from storage.seed_encryption import encrypt_session_seeds

    log.debug("encrypt_seeds", "Encrypting session seeds")
    for session in cache_codec._SESSIONS:
        encrypt_session_seeds(session)
    encrypt_session_seeds(get_sessionless_cache())


def decrypt_seeds() -> None:
    """
    Decrypts seeds in all the cached sessions and the sessionless cache.
    """
    from storage.seed_encryption import decrypt_session_seeds

    log.debug("decrypt_seeds", "Decrypting session seeds")
    for session in cache_codec._SESSIONS:
        decrypt_session_seeds(session)
    decrypt_session_seeds(get_sessionless_cache())


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
