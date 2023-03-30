import gc
from micropython import const
from typing import TYPE_CHECKING

from trezor import utils

if TYPE_CHECKING:
    from typing import Sequence, TypeVar, overload

    T = TypeVar("T")


_MAX_SESSIONS_COUNT = const(10)
_SESSIONLESS_FLAG = const(128)
_SESSION_ID_LENGTH = const(32)

# Traditional cache keys
APP_COMMON_SEED = const(0)
APP_COMMON_AUTHORIZATION_TYPE = const(1)
APP_COMMON_AUTHORIZATION_DATA = const(2)
APP_COMMON_NONCE = const(3)
if not utils.BITCOIN_ONLY:
    APP_COMMON_DERIVE_CARDANO = const(4)
    APP_CARDANO_ICARUS_SECRET = const(5)
    APP_CARDANO_ICARUS_TREZOR_SECRET = const(6)
    APP_MONERO_LIVE_REFRESH = const(7)

# Keys that are valid across sessions
APP_COMMON_SEED_WITHOUT_PASSPHRASE = const(0 | _SESSIONLESS_FLAG)
APP_COMMON_SAFETY_CHECKS_TEMPORARY = const(1 | _SESSIONLESS_FLAG)
STORAGE_DEVICE_EXPERIMENTAL_FEATURES = const(2 | _SESSIONLESS_FLAG)
APP_COMMON_REQUEST_PIN_LAST_UNLOCK = const(3 | _SESSIONLESS_FLAG)
APP_COMMON_BUSY_DEADLINE_MS = const(4 | _SESSIONLESS_FLAG)
APP_MISC_COSI_NONCE = const(5 | _SESSIONLESS_FLAG)
APP_MISC_COSI_COMMITMENT = const(6 | _SESSIONLESS_FLAG)


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


class InvalidSessionError(Exception):
    pass


class DataCache:
    fields: Sequence[int]

    def __init__(self) -> None:
        self.data = [bytearray(f + 1) for f in self.fields]

    def set(self, key: int, value: bytes) -> None:
        utils.ensure(key < len(self.fields))
        utils.ensure(len(value) <= self.fields[key])
        self.data[key][0] = 1
        self.data[key][1:] = value

    if TYPE_CHECKING:

        @overload
        def get(self, key: int) -> bytes | None:
            ...

        @overload
        def get(self, key: int, default: T) -> bytes | T:  # noqa: F811
            ...

    def get(self, key: int, default: T | None = None) -> bytes | T | None:  # noqa: F811
        utils.ensure(key < len(self.fields))
        if self.data[key][0] != 1:
            return default
        return bytes(self.data[key][1:])

    def is_set(self, key: int) -> bool:
        utils.ensure(key < len(self.fields))
        return self.data[key][0] == 1

    def delete(self, key: int) -> None:
        utils.ensure(key < len(self.fields))
        self.data[key][:] = b"\x00"

    def clear(self) -> None:
        for i in range(len(self.fields)):
            self.delete(i)


class SessionCache(DataCache):
    def __init__(self) -> None:
        self.session_id = bytearray(_SESSION_ID_LENGTH)
        if utils.BITCOIN_ONLY:
            self.fields = (
                64,  # APP_COMMON_SEED
                2,  # APP_COMMON_AUTHORIZATION_TYPE
                128,  # APP_COMMON_AUTHORIZATION_DATA
                32,  # APP_COMMON_NONCE
            )
        else:
            self.fields = (
                64,  # APP_COMMON_SEED
                2,  # APP_COMMON_AUTHORIZATION_TYPE
                128,  # APP_COMMON_AUTHORIZATION_DATA
                32,  # APP_COMMON_NONCE
                1,  # APP_COMMON_DERIVE_CARDANO
                96,  # APP_CARDANO_ICARUS_SECRET
                96,  # APP_CARDANO_ICARUS_TREZOR_SECRET
                1,  # APP_MONERO_LIVE_REFRESH
            )
        self.last_usage = 0
        super().__init__()

    def export_session_id(self) -> bytes:
        from trezorcrypto import random  # avoid pulling in trezor.crypto

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
            1,  # STORAGE_DEVICE_EXPERIMENTAL_FEATURES
            8,  # APP_COMMON_REQUEST_PIN_LAST_UNLOCK
            8,  # APP_COMMON_BUSY_DEADLINE_MS
            32,  # APP_MISC_COSI_NONCE
            32,  # APP_MISC_COSI_COMMITMENT
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


def set(key: int, value: bytes) -> None:
    if key & _SESSIONLESS_FLAG:
        _SESSIONLESS_CACHE.set(key ^ _SESSIONLESS_FLAG, value)
        return
    if _active_session_idx is None:
        raise InvalidSessionError
    _SESSIONS[_active_session_idx].set(key, value)


def set_int(key: int, value: int) -> None:
    if key & _SESSIONLESS_FLAG:
        length = _SESSIONLESS_CACHE.fields[key ^ _SESSIONLESS_FLAG]
    elif _active_session_idx is None:
        raise InvalidSessionError
    else:
        length = _SESSIONS[_active_session_idx].fields[key]

    encoded = value.to_bytes(length, "big")

    # Ensure that the value fits within the length. Micropython's int.to_bytes()
    # doesn't raise OverflowError.
    assert int.from_bytes(encoded, "big") == value

    set(key, encoded)


if TYPE_CHECKING:

    @overload
    def get(key: int) -> bytes | None:
        ...

    @overload
    def get(key: int, default: T) -> bytes | T:  # noqa: F811
        ...


def get(key: int, default: T | None = None) -> bytes | T | None:  # noqa: F811
    if key & _SESSIONLESS_FLAG:
        return _SESSIONLESS_CACHE.get(key ^ _SESSIONLESS_FLAG, default)
    if _active_session_idx is None:
        raise InvalidSessionError
    return _SESSIONS[_active_session_idx].get(key, default)


def get_int(key: int, default: T | None = None) -> int | T | None:  # noqa: F811
    encoded = get(key)
    if encoded is None:
        return default
    else:
        return int.from_bytes(encoded, "big")


def is_set(key: int) -> bool:
    if key & _SESSIONLESS_FLAG:
        return _SESSIONLESS_CACHE.is_set(key ^ _SESSIONLESS_FLAG)
    if _active_session_idx is None:
        raise InvalidSessionError
    return _SESSIONS[_active_session_idx].is_set(key)


def delete(key: int) -> None:
    if key & _SESSIONLESS_FLAG:
        return _SESSIONLESS_CACHE.delete(key ^ _SESSIONLESS_FLAG)
    if _active_session_idx is None:
        raise InvalidSessionError
    return _SESSIONS[_active_session_idx].delete(key)


if TYPE_CHECKING:
    from typing import Awaitable, Callable, TypeVar, ParamSpec

    P = ParamSpec("P")
    ByteFunc = Callable[P, bytes]
    AsyncByteFunc = Callable[P, Awaitable[bytes]]


def stored(key: int) -> Callable[[ByteFunc[P]], ByteFunc[P]]:
    def decorator(func: ByteFunc[P]) -> ByteFunc[P]:
        def wrapper(*args: P.args, **kwargs: P.kwargs):
            value = get(key)
            if value is None:
                value = func(*args, **kwargs)
                set(key, value)
            return value

        return wrapper

    return decorator


def stored_async(key: int) -> Callable[[AsyncByteFunc[P]], AsyncByteFunc[P]]:
    def decorator(func: AsyncByteFunc[P]) -> AsyncByteFunc[P]:
        async def wrapper(*args: P.args, **kwargs: P.kwargs):
            value = get(key)
            if value is None:
                value = await func(*args, **kwargs)
                set(key, value)
            return value

        return wrapper

    return decorator


def clear_all() -> None:
    global _active_session_idx

    _active_session_idx = None
    _SESSIONLESS_CACHE.clear()
    for session in _SESSIONS:
        session.clear()
