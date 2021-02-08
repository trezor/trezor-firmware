from trezor.wire.errors import InvalidSession
from trezor.crypto import random

if False:
    from typing import Optional, Dict, List, Any

_MAX_SESSIONS_COUNT = 10
_SESSIONLESS_FLAG = 128

# Traditional cache keys
APP_COMMON_SEED = 0
APP_CARDANO_ROOT = 1
APP_MONERO_LIVE_REFRESH = 2
APP_BASE_AUTHORIZATION = 3

# Keys that are valid across sessions
APP_COMMON_SEED_WITHOUT_PASSPHRASE = 1 | _SESSIONLESS_FLAG
APP_COMMON_SAFETY_CHECKS_TEMPORARY = 2 | _SESSIONLESS_FLAG

state: Dict = {}


def set_state(new_state: Dict) -> None:
    global state
    state = new_state
    if 'active_session_id' not in state:
        reset_state()


def reset_state():
    # active_session_id: Optional[bytes] = None
    # caches: Dict[bytes, Dict[int, Any]] = {}
    # session_ids: List[bytes] = []
    # sessionless_cache: Dict[int, Any] = {}
    state['active_session_id'] = None
    state['caches'] = {}
    state['session_ids'] = []
    state['sessionless_cache'] = {}


if False:
    from typing import Any, Callable, TypeVar

    F = TypeVar("F", bound=Callable[..., Any])


def _move_session_ids_queue(session_id: bytes) -> None:
    # Move the LRU session ids queue.
    if session_id in state['session_ids']:
        state['session_ids'].remove(session_id)

    while len(state['session_ids']) >= _MAX_SESSIONS_COUNT:
        remove_session_id = state['session_ids'].pop()
        del state['caches'][remove_session_id]

    state['session_ids'].insert(0, session_id)


def start_session(received_session_id: bytes = None) -> bytes:
    if received_session_id and received_session_id in state['session_ids']:
        session_id = received_session_id
    else:
        session_id = random.bytes(32)
        state['caches'][session_id] = {}

    state['active_session_id'] = session_id
    _move_session_ids_queue(session_id)
    return state['active_session_id']


def end_current_session() -> None:
    if state['active_session_id'] is None:
        return
    current_session_id = state['active_session_id']
    state['active_session_id'] = None
    state['session_ids'].remove(current_session_id)
    del state['caches'][current_session_id]


def is_session_started() -> bool:
    return state['active_session_id'] is not None


def set(key: int, value: Any) -> None:
    if key & _SESSIONLESS_FLAG:
        state['sessionless_cache'][key] = value
        return
    if state['active_session_id'] is None:
        raise wire.InvalidSession
    state['caches'][state['active_session_id']][key] = value


def get(key: int) -> Any:
    if key & _SESSIONLESS_FLAG:
        return state['sessionless_cache'].get(key)
    if state['active_session_id'] is None:
        raise wire.InvalidSession
    return state['caches'][state['active_session_id']].get(key)


def delete(key: int) -> None:
    if key & _SESSIONLESS_FLAG:
        if key in state['sessionless_cache']:
            del state['sessionless_cache'][key]
        return
    if state['active_session_id'] is None:
        raise wire.InvalidSession
    if key in state['caches'][state['active_session_id']]:
        del state['caches'][state['active_session_id']][key]


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
    state['active_session_id'] = None
    state['caches'].clear()
    state['session_ids'].clear()
    state['sessionless_cache'].clear()
