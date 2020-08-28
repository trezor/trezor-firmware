from trezor import wire
from trezor.crypto import random

if False:
    from typing import Optional, Dict, List

_MAX_SESSIONS_COUNT = 10
_SESSIONLESS_FLAG = 128

# Traditional cache keys
APP_COMMON_SEED = 0
APP_CARDANO_ROOT = 1
APP_MONERO_LIVE_REFRESH = 2
APP_BASE_AUTHORIZATION = 3

# Keys that are valid across sessions
APP_COMMON_SEED_WITHOUT_PASSPHRASE = 1 | _SESSIONLESS_FLAG


_active_session_id = None  # type: Optional[bytes]
_caches = {}  # type: Dict[bytes, Dict[int, Any]]
_session_ids = []  # type: List[bytes]
_sessionless_cache = {}  # type: Dict[int, Any]

if False:
    from typing import Any, Callable, TypeVar

    F = TypeVar("F", bound=Callable[..., Any])


def _move_session_ids_queue(session_id: bytes) -> None:
    # Move the LRU session ids queue.
    if session_id in _session_ids:
        _session_ids.remove(session_id)

    while len(_session_ids) >= _MAX_SESSIONS_COUNT:
        remove_session_id = _session_ids.pop()
        del _caches[remove_session_id]

    _session_ids.insert(0, session_id)


def start_session(received_session_id: bytes = None) -> bytes:
    if received_session_id and received_session_id in _session_ids:
        session_id = received_session_id
    else:
        session_id = random.bytes(32)
        _caches[session_id] = {}

    global _active_session_id
    _active_session_id = session_id
    _move_session_ids_queue(session_id)
    return _active_session_id


def end_current_session() -> None:
    global _active_session_id

    if _active_session_id is None:
        return

    current_session_id = _active_session_id
    _active_session_id = None

    _session_ids.remove(current_session_id)
    del _caches[current_session_id]


def is_session_started() -> bool:
    return _active_session_id is not None


def set(key: int, value: Any) -> None:
    if key & _SESSIONLESS_FLAG:
        _sessionless_cache[key] = value
        return
    if _active_session_id is None:
        raise wire.InvalidSession
    _caches[_active_session_id][key] = value


def get(key: int) -> Any:
    if key & _SESSIONLESS_FLAG:
        return _sessionless_cache.get(key)
    if _active_session_id is None:
        raise wire.InvalidSession
    return _caches[_active_session_id].get(key)


def delete(key: int) -> None:
    if key & _SESSIONLESS_FLAG:
        if key in _sessionless_cache:
            del _sessionless_cache[key]
        return
    if _active_session_id is None:
        raise wire.InvalidSession
    if key in _caches[_active_session_id]:
        del _caches[_active_session_id][key]


def stored(key: int) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        # if we didn't check this, it would be easy to store an Awaitable[something]
        # in cache, which might prove hard to debug
        assert not isinstance(func, type(lambda: (yield))), "use stored_async instead"

        def wrapper(*args, **kwargs):  # type: ignore
            value = get(key)
            if value is None:
                value = func(*args, **kwargs)
                set(key, value)
            return value

        return wrapper  # type: ignore

    return decorator


def stored_async(key: int) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        # assert isinstance(func, type(lambda: (yield))), "do not use stored_async"
        # XXX the test above fails for closures
        # We shouldn't need this test here anyway: the 'await func()' should fail
        # with functions that do not return an awaitable so the problem is more visible.

        async def wrapper(*args, **kwargs):  # type: ignore
            value = get(key)
            if value is None:
                value = await func(*args, **kwargs)
                set(key, value)
            return value

        return wrapper  # type: ignore

    return decorator


def clear_all() -> None:
    global _active_session_id
    global _caches
    global _session_ids
    global _sessionless_cache

    _active_session_id = None
    _caches.clear()
    _session_ids.clear()
    _sessionless_cache.clear()
