import builtins
from micropython import const
from typing import TYPE_CHECKING

from storage.cache_common import (
    CHANNEL_HOST_STATIC_PUBKEY,
    CHANNEL_ID,
    CHANNEL_STATE,
    CHANNEL_SYNC,
    SESSION_ID,
    SESSION_STATE,
    DataCache,
)

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Sequence

# THP specific constants
_MAX_CHANNELS_COUNT = const(10)
_MAX_SESSIONS_COUNT = const(20)

_CHANNEL_ID_LENGTH = const(2)
SESSION_ID_LENGTH = const(1)
KEY_LENGTH = const(32)
TAG_LENGTH = const(16)

_UNALLOCATED_STATE = const(0)
_ALLOCATED_STATE = const(1)
_SEEDLESS_STATE = const(2)

_MAX_CHANNEL_ID = const(0xFFEF)
# Channel IDs from 0xFFF0 to 0xFFFE, and 0x0000, are reserved for future use
BROADCAST_CHANNEL_ID = const(0xFFFF)


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


class ChannelCache(ThpDataCache):

    def __init__(self) -> None:
        self.fields = (
            2,  # CHANNEL_ID
            1,  # CHANNEL_STATE
            1,  # CHANNEL_IFACE
            1,  # CHANNEL_SYNC
            32,  # CHANNEL_HANDSHAKE_HASH
            32,  # CHANNEL_KEY_RECEIVE
            32,  # CHANNEL_KEY_SEND
            8,  # CHANNEL_NONCE_RECEIVE
            8,  # CHANNEL_NONCE_SEND
            32,  # CHANNEL_HOST_STATIC_PUBKEY
            2,  # CHANNEL_ACK_LATENCY_MS
        )
        super().__init__()
        self.set_int(CHANNEL_SYNC, 0x80)

    @property
    def sync(self) -> int:
        # can_send_bit | sync_receive_bit | sync_send_bit | ack_piggybacking | rfu(4)
        return self.get_int(CHANNEL_SYNC) or 0x00

    @sync.setter
    def sync(self, value: int) -> None:
        self.set_int(CHANNEL_SYNC, value)

    def set_host_static_public_key(self, key: memoryview) -> None:
        if len(key) != KEY_LENGTH:
            raise ValueError("Invalid key length")
        self.set(CHANNEL_HOST_STATIC_PUBKEY, key)


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


_CHANNELS: list[ChannelCache] = []
_SESSIONS: list[SessionThpCache] = []
cid_counter: int = 0

# Last-used counter
_usage_counter = 0


def initialize() -> None:
    global cid_counter

    for _ in range(_MAX_CHANNELS_COUNT):
        _CHANNELS.append(ChannelCache())
    for _ in range(_MAX_SESSIONS_COUNT):
        _SESSIONS.append(SessionThpCache())

    for channel in _CHANNELS:
        channel.clear()
    for session in _SESSIONS:
        session.clear()

    from trezorcrypto import random

    cid_counter = random.uniform(_MAX_CHANNEL_ID)


def get_new_channel() -> ChannelCache:

    new_cid = get_next_channel_id()
    index = _get_next_channel_index()

    # clear sessions from replaced channel
    if (
        _CHANNELS[index].get_int(CHANNEL_STATE, _UNALLOCATED_STATE)
        != _UNALLOCATED_STATE
    ):
        old_cid = _CHANNELS[index].channel_id
        clear_sessions_with_channel_id(old_cid)

    _CHANNELS[index] = ChannelCache()
    _CHANNELS[index].set(CHANNEL_ID, new_cid)
    _CHANNELS[index].last_usage = _get_usage_counter_and_increment()
    _CHANNELS[index].set_int(CHANNEL_STATE, _UNALLOCATED_STATE)
    return _CHANNELS[index]


def update_channel_last_used(channel_id: AnyBytes) -> None:
    for channel in _CHANNELS:
        if channel.channel_id == channel_id:
            channel.last_usage = _get_usage_counter_and_increment()
            return


def update_session_last_used(channel_id: AnyBytes, session_id: AnyBytes) -> None:
    for session in _SESSIONS:
        if session.channel_id == channel_id and session.session_id == session_id:
            session.last_usage = _get_usage_counter_and_increment()
            update_channel_last_used(channel_id)
            return


def find_allocated_channel(cid: int) -> ChannelCache | None:
    for channel in _CHANNELS:
        state = channel.get_int(CHANNEL_STATE, _UNALLOCATED_STATE)
        if state == _UNALLOCATED_STATE:
            continue
        if channel.get_int(CHANNEL_ID) == cid:
            return channel
    return None


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


def create_or_replace_session(
    channel: ChannelCache, session_id: bytes
) -> SessionThpCache:
    index = get_allocated_session_index(channel.channel_id, session_id)
    if index is None:
        index = _get_next_session_index()

    _SESSIONS[index] = SessionThpCache()
    _SESSIONS[index].set(CHANNEL_ID, channel.channel_id)
    _SESSIONS[index].set(SESSION_ID, session_id)
    _SESSIONS[index].last_usage = _get_usage_counter_and_increment()
    channel.last_usage = (
        _get_usage_counter_and_increment()
    )  # increment also use of the channel so it does not get replaced

    _SESSIONS[index].set_int(SESSION_STATE, _ALLOCATED_STATE)
    return _SESSIONS[index]


def _migrate_sessions(old_channel: ChannelCache, new_channel: ChannelCache) -> None:
    for session in _SESSIONS:
        if session.channel_id == old_channel.channel_id:
            session.set(CHANNEL_ID, new_channel.channel_id)


def _replace_channel(old_channel: ChannelCache, new_channel: ChannelCache) -> None:
    _migrate_sessions(old_channel, new_channel)
    old_channel.clear()


def conditionally_replace_channel(
    new_channel: ChannelCache, required_state: int, required_key: int
) -> bool:
    """Replaces "old channel" cache entry with a `new_channel` if two conditions are met:

    1. The "old channel" is in a state `required_state`
    2. The "old channel" has the same value for `required_key` as the `new_channel`


    Returns: bool - whether any channel was replaced.
    """
    was_any_channel_replaced: bool = False
    for channel in _CHANNELS:
        if channel.channel_id == new_channel.channel_id:
            continue
        if channel.get_int(CHANNEL_STATE) == required_state and channel.get(
            required_key
        ) == new_channel.get(required_key):
            _replace_channel(channel, new_channel)
            was_any_channel_replaced = True
    return was_any_channel_replaced


def is_there_a_channel_to_replace(
    new_channel: ChannelCache, required_state: int, required_key: int
) -> bool:
    for channel in _CHANNELS:
        if channel.channel_id == new_channel.channel_id:
            continue
        if channel.get_int(CHANNEL_STATE) == required_state and channel.get(
            required_key
        ) == new_channel.get(required_key):
            return True
    return False


def _get_usage_counter_and_increment() -> int:
    global _usage_counter
    _usage_counter += 1
    return _usage_counter


def _get_next_channel_index() -> int:
    idx = _get_unallocated_channel_index()
    if idx is not None:
        return idx
    return _get_least_recently_used_item(_CHANNELS, max_count=_MAX_CHANNELS_COUNT)


def _get_next_session_index() -> int:
    idx = _get_unallocated_session_index()
    if idx is not None:
        return idx
    return _get_least_recently_used_item(_SESSIONS, max_count=_MAX_SESSIONS_COUNT)


def _get_unallocated_channel_index() -> int | None:
    for i in range(_MAX_CHANNELS_COUNT):
        if (
            _CHANNELS[i].get_int(CHANNEL_STATE, _UNALLOCATED_STATE)
            == _UNALLOCATED_STATE
        ):
            return i
    return None


def _get_unallocated_session_index() -> int | None:
    for i in range(_MAX_SESSIONS_COUNT):
        if (_SESSIONS[i]) is _UNALLOCATED_STATE:
            return i
    return None


def get_next_channel_id() -> bytes:
    global cid_counter
    while True:
        cid_counter += 1
        if cid_counter > _MAX_CHANNEL_ID:
            cid_counter = 1
        if _is_cid_unique():
            break
    return cid_counter.to_bytes(_CHANNEL_ID_LENGTH, "big")


def _is_cid_unique() -> bool:
    cid_counter_bytes = cid_counter.to_bytes(_CHANNEL_ID_LENGTH, "big")
    for channel in _CHANNELS:
        if channel.channel_id == cid_counter_bytes:
            return False
    return True


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
    for channel in _CHANNELS:
        channel.clear()


def clear_all_except_one_session_keys(excluded: tuple[AnyBytes, AnyBytes]) -> None:
    cid, sid = excluded

    for channel in _CHANNELS:
        if channel.channel_id != cid:
            channel.clear()

    for session in _SESSIONS:
        if session.channel_id != cid or session.session_id != sid:
            session.clear()
        else:
            s_last_usage = session.last_usage
            session.clear()
            session.last_usage = s_last_usage
