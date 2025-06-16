import builtins
import gc
from typing import TYPE_CHECKING

from storage.cache_common import SESSIONLESS_FLAG, SessionlessCache
from trezor import utils

if TYPE_CHECKING:
    from typing import Tuple

    pass

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


def clear_all(excluded: Tuple[bytes, bytes] | None = None) -> None:
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
