from trezor.crypto import random

if False:
    from typing import Optional, Dict, List

_MAX_SESSIONS_COUNT = 10
_SESSIONLESS_FLAG = 128

# Traditional cache keys
APP_COMMON_SEED = 0
APP_CARDANO_ROOT = 1
APP_MONERO_LIVE_REFRESH = 2

# Keys that are valid across sessions
APP_COMMON_SEED_WITHOUT_PASSPHRASE = 1 | _SESSIONLESS_FLAG


_active_session_id = None  # type: Optional[bytes]
_caches = {}  # type: Dict[bytes, Dict[int, Any]]
_session_ids = []  # type: List[bytes]
_sessionless_cache = {}  # type: Dict[int, Any]

if False:
    from typing import Any


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


def is_session_started() -> bool:
    return _active_session_id is not None


def set(key: int, value: Any) -> None:
    if key & _SESSIONLESS_FLAG:
        _sessionless_cache[key] = value
        return
    if _active_session_id is None:
        raise RuntimeError  # no session active
    _caches[_active_session_id][key] = value


def get(key: int) -> Any:
    if key & _SESSIONLESS_FLAG:
        return _sessionless_cache.get(key)
    if _active_session_id is None:
        raise RuntimeError  # no session active
    return _caches[_active_session_id].get(key)


def clear_all() -> None:
    global _active_session_id
    global _caches
    global _session_ids
    global _sessionless_cache

    _active_session_id = None
    _caches.clear()
    _session_ids.clear()
    _sessionless_cache.clear()
