import gc
from trezorcrypto import random  # avoid pulling in trezor.crypto

from trezor import utils

if False:
    from typing import Sequence

_MAX_SESSIONS_COUNT = 10
_SESSIONLESS_FLAG = 128
_SESSION_ID_LENGTH = 32

# Traditional cache keys
APP_COMMON_SEED = 0
APP_CARDANO_PASSPHRASE = 1
APP_MONERO_LIVE_REFRESH = 2
APP_BASE_AUTHORIZATION = 3

# Keys that are valid across sessions
APP_COMMON_SEED_WITHOUT_PASSPHRASE = 0 | _SESSIONLESS_FLAG
APP_COMMON_SAFETY_CHECKS_TEMPORARY = 1 | _SESSIONLESS_FLAG


class InvalidSessionError(Exception):
    pass


class DataCache:
    fields: Sequence[int]

    def __init__(self) -> None:
        self.data = [bytearray(f) for f in self.fields]

    def set(self, key: int, value: bytes) -> None:
        utils.ensure(key < len(self.fields))
        utils.ensure(len(value) <= self.fields[key])
        self.data[key][:] = value

    def get(self, key: int) -> bytes:
        utils.ensure(key < len(self.fields), "failed to load key %d" % key)
        return bytes(self.data[key])

    def clear(self) -> None:
        for i in range(len(self.fields)):
            self.set(i, b"")


class SessionCache(DataCache):
    def __init__(self) -> None:
        self.session_id = bytearray(_SESSION_ID_LENGTH)
        self.fields = (
            64,  # APP_COMMON_SEED
            50,  # APP_CARDANO_PASSPHRASE
            1,  # APP_MONERO_LIVE_REFRESH
            128,  # APP_BASE_AUTHORIZATION
        )
        self.last_usage = 0
        super().__init__()

    def export_session_id(self) -> bytes:
        # generate a new session id if we don't have it yet
        if not self.session_id:
            self.session_id[:] = random.bytes(_SESSION_ID_LENGTH)
        # export it as immutable bytes
        return bytes(self.session_id)

    def clear(self) -> None:
        super().clear()
        self.last_usage = 0
        self.session_id[:] = b""


class SessionlessCache(DataCache):
    def __init__(self) -> None:
        self.fields = (
            64,  # APP_COMMON_SEED_WITHOUT_PASSPHRASE
            1,  # APP_COMMON_SAFETY_CHECKS_TEMPORARY
        )
        super().__init__()


# XXX
# Allocation notes:
# Instantiation of a DataCache subclass should make as little garbage as possible, so
# that the preallocated bytearrays are compact in memory.
# That is why the initialization is two-step: first create appropriately sized
# bytearrays, then later call `clear()` on all the existing objects, which resets them
# to zero length. This is producing some trash - `b[:]` allocates a slice.

_SESSIONS: list[SessionCache] = []
for _ in range(_MAX_SESSIONS_COUNT):
    _SESSIONS.append(SessionCache())

_SESSIONLESS_CACHE = SessionlessCache()

for session in _SESSIONS:
    session.clear()
_SESSIONLESS_CACHE.clear()

gc.collect()


_active_session_idx: int | None = None
_session_usage_counter = 0


def start_session(received_session_id: bytes | None = None) -> bytes:
    global _active_session_idx
    global _session_usage_counter

    if (
        received_session_id is not None
        and len(received_session_id) != _SESSION_ID_LENGTH
    ):
        # Prevent the caller from setting received_session_id=b"" and finding a cleared
        # session. More generally, short-circuit the session id search, because we know
        # that wrong-length session ids should not be in cache.
        # Reduce to "session id not provided" case because that's what we do when
        # caller supplies an id that is not found.
        received_session_id = None

    _session_usage_counter += 1

    # attempt to find specified session id
    if received_session_id:
        for i in range(_MAX_SESSIONS_COUNT):
            if _SESSIONS[i].session_id == received_session_id:
                _active_session_idx = i
                _SESSIONS[i].last_usage = _session_usage_counter
                return received_session_id

    # allocate least recently used session
    lru_counter = _session_usage_counter
    lru_session_idx = 0
    for i in range(_MAX_SESSIONS_COUNT):
        if _SESSIONS[i].last_usage < lru_counter:
            lru_counter = _SESSIONS[i].last_usage
            lru_session_idx = i

    _active_session_idx = lru_session_idx
    selected_session = _SESSIONS[lru_session_idx]
    selected_session.clear()
    selected_session.last_usage = _session_usage_counter
    return selected_session.export_session_id()


def end_current_session() -> None:
    global _active_session_idx

    if _active_session_idx is None:
        return

    _SESSIONS[_active_session_idx].clear()
    _active_session_idx = None


def is_session_started() -> bool:
    return _active_session_idx is not None


def set(key: int, value: bytes) -> None:
    if key & _SESSIONLESS_FLAG:
        _SESSIONLESS_CACHE.set(key ^ _SESSIONLESS_FLAG, value)
        return
    if _active_session_idx is None:
        raise InvalidSessionError
    _SESSIONS[_active_session_idx].set(key, value)


def get(key: int) -> bytes:
    if key & _SESSIONLESS_FLAG:
        return _SESSIONLESS_CACHE.get(key ^ _SESSIONLESS_FLAG)
    if _active_session_idx is None:
        raise InvalidSessionError
    return _SESSIONS[_active_session_idx].get(key)


if False:
    from typing import Awaitable, Callable, TypeVar

    ByteFunc = TypeVar("ByteFunc", bound=Callable[..., bytes])
    AsyncByteFunc = TypeVar("AsyncByteFunc", bound=Callable[..., Awaitable[bytes]])


def stored(key: int) -> Callable[[ByteFunc], ByteFunc]:
    def decorator(func: ByteFunc) -> ByteFunc:
        # if we didn't check this, it would be easy to store an Awaitable[something]
        # in cache, which might prove hard to debug
        # XXX mypy should be checking this now, but we don't have full coverage yet
        assert not isinstance(func, type(lambda: (yield))), "use stored_async instead"

        def wrapper(*args, **kwargs):  # type: ignore
            value = get(key)
            if not value:
                value = func(*args, **kwargs)
                set(key, value)
            return value

        return wrapper  # type: ignore

    return decorator


def stored_async(key: int) -> Callable[[AsyncByteFunc], AsyncByteFunc]:
    def decorator(func: AsyncByteFunc) -> AsyncByteFunc:
        # assert isinstance(func, type(lambda: (yield))), "do not use stored_async"
        # XXX the test above fails for closures
        # We shouldn't need this test here anyway: the 'await func()' should fail
        # with functions that do not return an awaitable so the problem is more visible.

        async def wrapper(*args, **kwargs):  # type: ignore
            value = get(key)
            if not value:
                value = await func(*args, **kwargs)
                set(key, value)
            return value

        return wrapper  # type: ignore

    return decorator


def clear_all() -> None:
    global _active_session_idx

    _active_session_idx = None
    _SESSIONLESS_CACHE.clear()
    for session in _SESSIONS:
        session.clear()
