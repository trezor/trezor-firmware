import builtins
from micropython import const
from typing import TYPE_CHECKING

from storage.cache_common import CHANNEL_ID, SESSION_ID, SESSION_STATE, DataCache

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Sequence

# THP specific constants
_MAX_SESSIONS_COUNT = const(20)

_CHANNEL_ID_LENGTH = const(2)
SESSION_ID_LENGTH = const(1)

_UNALLOCATED_STATE = const(0)
_ALLOCATED_STATE = const(1)
_SEEDLESS_STATE = const(2)


class ThpDataCache(DataCache):

    def __init__(self) -> None:
        self.last_usage = 0
        super().__init__()

    @property
    def channel_id(self) -> bytes:
        return self.get(CHANNEL_ID) or b""

    def clear(self) -> None:
        self.last_usage = 0
        super().clear()


class SessionThpCache(ThpDataCache):
    def __init__(self) -> None:
        from trezor import utils

        if utils.BITCOIN_ONLY:
            self.fields = (
                2,  # CHANNEL_ID
                1,  # SESSION_ID
                1,  # SESSION_STATE
                64,  # APP_COMMON_SEED
                2,  # APP_COMMON_AUTHORIZATION_TYPE
                128,  # APP_COMMON_AUTHORIZATION_DATA
                32,  # APP_COMMON_NONCE
            )
        else:
            self.fields = (
                2,  # CHANNEL_ID
                1,  # SESSION_ID
                1,  # SESSION_STATE
                64,  # APP_COMMON_SEED
                2,  # APP_COMMON_AUTHORIZATION_TYPE
                128,  # APP_COMMON_AUTHORIZATION_DATA
                32,  # APP_COMMON_NONCE
                0,  # APP_COMMON_DERIVE_CARDANO
                96,  # APP_CARDANO_ICARUS_SECRET
                96,  # APP_CARDANO_ICARUS_TREZOR_SECRET
                0,  # APP_MONERO_LIVE_REFRESH
            )
        super().__init__()

    @property
    def session_id(self) -> bytes:
        return self.get(SESSION_ID) or b""

    def clear(self) -> None:
        super().clear()


_SESSIONS: list[SessionThpCache] = []

# Last-used counter
_usage_counter = 0


def initialize() -> None:
    for _ in range(_MAX_SESSIONS_COUNT):
        _SESSIONS.append(SessionThpCache())

    for session in _SESSIONS:
        session.clear()


def update_channel_last_used(channel_id: AnyBytes) -> None:
    from trezorthp import channel_update_last_usage

    channel_update_last_usage(int.from_bytes(channel_id, "big"))


def update_session_last_used(channel_id: AnyBytes, session_id: AnyBytes) -> None:
    for session in _SESSIONS:
        if session.channel_id == channel_id and session.session_id == session_id:
            session.last_usage = _get_usage_counter_and_increment()
            update_channel_last_used(channel_id)
            return


def get_allocated_session(
    channel_id: bytes, session_id: bytes
) -> SessionThpCache | None:
    index = get_allocated_session_index(channel_id, session_id)
    if index is None:
        return index
    return _SESSIONS[index]


def get_allocated_session_index(channel_id: bytes, session_id: bytes) -> int | None:
    """
    Finds and returns index of the first allocated session matching the given `channel_id`
    and `session_id`, or `None` if no match is found.

    Raises `Exception` if either channel_id or session_id has an invalid length.
    """
    if len(channel_id) != _CHANNEL_ID_LENGTH or len(session_id) != SESSION_ID_LENGTH:
        raise ValueError("At least one of arguments has invalid length")

    for i in range(_MAX_SESSIONS_COUNT):
        if (
            _SESSIONS[i].get_int(SESSION_STATE, _UNALLOCATED_STATE)
            == _UNALLOCATED_STATE
        ):
            continue
        if _SESSIONS[i].channel_id != channel_id:
            continue
        if _SESSIONS[i].session_id != session_id:
            continue
        return i
    return None


def is_seedless_session(session_cache: SessionThpCache) -> bool:
    return session_cache.get_int(SESSION_STATE, _UNALLOCATED_STATE) == _SEEDLESS_STATE


def create_or_replace_session(channel_id: bytes, session_id: bytes) -> SessionThpCache:
    index = get_allocated_session_index(channel_id, session_id)
    if index is None:
        index = _get_next_session_index()

    _SESSIONS[index] = SessionThpCache()
    _SESSIONS[index].set(CHANNEL_ID, channel_id)
    _SESSIONS[index].set(SESSION_ID, session_id)
    _SESSIONS[index].last_usage = _get_usage_counter_and_increment()
    update_channel_last_used(channel_id)

    _SESSIONS[index].set_int(SESSION_STATE, _ALLOCATED_STATE)
    return _SESSIONS[index]


def migrate_sessions(old_channel_id: bytes, new_channel_id: bytes) -> None:
    for session in _SESSIONS:
        if session.channel_id == old_channel_id:
            session.set(CHANNEL_ID, new_channel_id)


def _get_usage_counter_and_increment() -> int:
    global _usage_counter
    _usage_counter += 1
    return _usage_counter


def _get_next_session_index() -> int:
    idx = _get_unallocated_session_index()
    if idx is not None:
        return idx
    return _get_least_recently_used_item(_SESSIONS, max_count=_MAX_SESSIONS_COUNT)


def _get_unallocated_session_index() -> int | None:
    for i in range(_MAX_SESSIONS_COUNT):
        if (_SESSIONS[i]) is _UNALLOCATED_STATE:
            return i
    return None


def _get_least_recently_used_item(list: Sequence[ThpDataCache], max_count: int) -> int:
    lru_counter = _usage_counter + 1
    lru_item_index = 0
    for i in range(max_count):
        if list[i].last_usage < lru_counter:
            lru_counter = list[i].last_usage
            lru_item_index = i
    return lru_item_index


def get_int_all_sessions(key: int) -> builtins.set[int]:
    values = builtins.set()
    for session in _SESSIONS:
        encoded = session.get(key)
        if encoded is not None:
            values.add(int.from_bytes(encoded, "big"))
    return values


def clear_sessions_with_channel_id(channel_id: bytes) -> None:
    for session in _SESSIONS:
        if session.channel_id == channel_id:
            session.clear()


def clear_session(session: SessionThpCache) -> None:
    for s in _SESSIONS:
        if s.channel_id == session.channel_id and s.session_id == session.session_id:
            session.clear()


def clear_all() -> None:
    for session in _SESSIONS:
        session.clear()

    from trezorthp import channel_close_all

    channel_close_all(None)


def clear_all_except_one_session_keys(excluded: tuple[AnyBytes, AnyBytes]) -> None:
    cid, sid = excluded

    from trezorthp import channel_close_all

    channel_close_all(int.from_bytes(cid, "big"))

    for session in _SESSIONS:
        if session.channel_id != cid or session.session_id != sid:
            session.clear()
        else:
            s_last_usage = session.last_usage
            session.clear()
            session.last_usage = s_last_usage
