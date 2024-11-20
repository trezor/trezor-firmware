import builtins
from micropython import const
from typing import TYPE_CHECKING

from storage.cache_common import DataCache
from trezor import utils

if TYPE_CHECKING:
    from typing import TypeVar

    T = TypeVar("T")


_MAX_SESSIONS_COUNT = const(10)
SESSION_ID_LENGTH = const(32)


class SessionCache(DataCache):
    """
    A cache for storing values that depend on seed derivation
    or are specific to a `protocol_v1` session.
    """

    def __init__(self) -> None:
        self.session_id = bytearray(SESSION_ID_LENGTH)
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
                0,  # APP_COMMON_DERIVE_CARDANO
                96,  # APP_CARDANO_ICARUS_SECRET
                96,  # APP_CARDANO_ICARUS_TREZOR_SECRET
                0,  # APP_MONERO_LIVE_REFRESH
            )
        self.last_usage = 0
        super().__init__()

    def export_session_id(self) -> bytes:
        from trezorcrypto import random  # avoid pulling in trezor.crypto

        # generate a new session id if we don't have it yet
        if not self.session_id:
            self.session_id[:] = random.bytes(SESSION_ID_LENGTH)
        # export it as immutable bytes
        return bytes(self.session_id)

    def clear(self) -> None:
        super().clear()
        self.last_usage = 0
        self.session_id[:] = b""


_SESSIONS: list[SessionCache] = []


def initialize() -> None:
    # Allocation notes:
    # Instantiation of any DataCache subclass should make as little garbage
    # as possible so that the preallocated bytearrays are compact in memory.
    # That is why the initialization is two-step: first, create appropriately
    # sized bytearrays, then call `clear()` on all existing objects, which
    # resets them to zero length. The `clear()` function uses `arr[:]`, which
    # allocates a slice.
    global _SESSIONS
    for _ in range(_MAX_SESSIONS_COUNT):
        _SESSIONS.append(SessionCache())

    for session in _SESSIONS:
        session.clear()


_active_session_idx: int | None = None
_session_usage_counter = 0


def get_active_session() -> SessionCache | None:
    if _active_session_idx is None:
        return None
    return _SESSIONS[_active_session_idx]


def start_session(received_session_id: bytes | None = None) -> bytes:
    global _active_session_idx
    global _session_usage_counter

    if (
        received_session_id is not None
        and len(received_session_id) != SESSION_ID_LENGTH
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


def get_int_all_sessions(key: int) -> builtins.set[int]:
    values = builtins.set()
    for session in _SESSIONS:
        encoded = session.get(key)
        if encoded is not None:
            values.add(int.from_bytes(encoded, "big"))
    return values


def clear_all() -> None:
    global _active_session_idx
    _active_session_idx = None
    for session in _SESSIONS:
        session.clear()
