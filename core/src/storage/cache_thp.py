import builtins
from micropython import const
from typing import TYPE_CHECKING

from storage.cache_common import CHANNEL_HOST_STATIC_PUBKEY, DataCache

if TYPE_CHECKING:
    from typing import Tuple

    pass


# THP specific constants
_MAX_CHANNELS_COUNT = const(10)
_MAX_SESSIONS_COUNT = const(20)


_CHANNEL_STATE_LENGTH = const(1)
_WIRE_INTERFACE_LENGTH = const(1)
_SESSION_STATE_LENGTH = const(1)
_CHANNEL_ID_LENGTH = const(2)
SESSION_ID_LENGTH = const(1)
BROADCAST_CHANNEL_ID = const(0xFFFF)
KEY_LENGTH = const(32)
TAG_LENGTH = const(16)
_UNALLOCATED_STATE = const(0)
_ALLOCATED_STATE = const(1)
_SEEDLESS_STATE = const(2)


class ThpDataCache(DataCache):
    def __init__(self) -> None:
        self.channel_id = bytearray(_CHANNEL_ID_LENGTH)
        self.last_usage = 0
        super().__init__()

    def clear(self) -> None:
        self.channel_id[:] = b""
        self.last_usage = 0
        super().clear()


class ChannelCache(ThpDataCache):

    def __init__(self) -> None:
        self.state = bytearray(_CHANNEL_STATE_LENGTH)
        self.iface = bytearray(1)  # TODO add decoding
        self.sync = 0x80  # can_send_bit | sync_receive_bit | sync_send_bit | rfu(5)
        self.fields = (
            32,  # CHANNEL_HANDSHAKE_HASH
            32,  # CHANNEL_KEY_RECEIVE
            32,  # CHANNEL_KEY_SEND
            8,  # CHANNEL_NONCE_RECEIVE
            8,  # CHANNEL_NONCE_SEND
            32,  # CHANNEL_HOST_STATIC_PUBKEY
        )
        super().__init__()

    def clear(self) -> None:
        self.state[:] = bytearray(
            int.to_bytes(0, _CHANNEL_STATE_LENGTH, "big")
        )  # Set state to UNALLOCATED
        self.state[:] = bytearray(_CHANNEL_STATE_LENGTH)
        self.iface[:] = bytearray(1)
        super().clear()

    def set_host_static_pubkey(self, key: bytearray) -> None:
        if len(key) != KEY_LENGTH:
            raise Exception("Invalid key length")
        self.set(CHANNEL_HOST_STATIC_PUBKEY, key)


class SessionThpCache(ThpDataCache):
    def __init__(self) -> None:
        from trezor import utils

        self.session_id = bytearray(SESSION_ID_LENGTH)
        self.state = bytearray(_SESSION_STATE_LENGTH)
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
        super().__init__()

    def clear(self) -> None:
        self.state[:] = bytearray(
            int.to_bytes(0, _SESSION_STATE_LENGTH, "big")
        )  # Set state to UNALLOCATED
        self.session_id[:] = b""
        super().clear()


_CHANNELS: list[ChannelCache] = []
_SESSIONS: list[SessionThpCache] = []
cid_counter: int = 0

# Last-used counter
_usage_counter = 0


def initialize() -> None:
    global _CHANNELS
    global _SESSIONS
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

    cid_counter = random.uniform(0xFFFE)


def get_new_channel(iface: bytes) -> ChannelCache:
    if len(iface) != _WIRE_INTERFACE_LENGTH:
        raise Exception("Invalid WireInterface (encoded) length")

    new_cid = get_next_channel_id()
    index = _get_next_channel_index()

    # clear sessions from replaced channel
    if _get_channel_state(_CHANNELS[index]) != _UNALLOCATED_STATE:
        old_cid = _CHANNELS[index].channel_id
        clear_sessions_with_channel_id(old_cid)

    _CHANNELS[index] = ChannelCache()
    _CHANNELS[index].channel_id[:] = new_cid
    _CHANNELS[index].last_usage = _get_usage_counter_and_increment()
    _CHANNELS[index].state[:] = bytearray(
        _UNALLOCATED_STATE.to_bytes(_CHANNEL_STATE_LENGTH, "big")
    )
    _CHANNELS[index].iface[:] = bytearray(iface)
    return _CHANNELS[index]


def update_channel_last_used(channel_id: bytes) -> None:
    for channel in _CHANNELS:
        if channel.channel_id == channel_id:
            channel.last_usage = _get_usage_counter_and_increment()
            return


def update_session_last_used(channel_id: bytes, session_id: bytes) -> None:
    for session in _SESSIONS:
        if session.channel_id == channel_id and session.session_id == session_id:
            session.last_usage = _get_usage_counter_and_increment()
            update_channel_last_used(channel_id)
            return


def get_all_allocated_channels() -> list[ChannelCache]:
    _list: list[ChannelCache] = []
    for channel in _CHANNELS:
        if _get_channel_state(channel) != _UNALLOCATED_STATE:
            _list.append(channel)
    return _list


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
        raise Exception("At least one of arguments has invalid length")

    for i in range(_MAX_SESSIONS_COUNT):
        if _get_session_state(_SESSIONS[i]) == _UNALLOCATED_STATE:
            continue
        if _SESSIONS[i].channel_id != channel_id:
            continue
        if _SESSIONS[i].session_id != session_id:
            continue
        return i
    return None


def is_seedless_session(session_cache: SessionThpCache) -> bool:
    return _get_session_state(session_cache) == _SEEDLESS_STATE


def create_or_replace_session(
    channel: ChannelCache, session_id: bytes
) -> SessionThpCache:
    index = get_allocated_session_index(channel.channel_id, session_id)
    if index is None:
        index = _get_next_session_index()

    _SESSIONS[index] = SessionThpCache()
    _SESSIONS[index].channel_id[:] = channel.channel_id
    _SESSIONS[index].session_id[:] = session_id
    _SESSIONS[index].last_usage = _get_usage_counter_and_increment()
    channel.last_usage = (
        _get_usage_counter_and_increment()
    )  # increment also use of the channel so it does not get replaced

    _SESSIONS[index].state[:] = bytearray(
        _ALLOCATED_STATE.to_bytes(_SESSION_STATE_LENGTH, "big")
    )
    return _SESSIONS[index]


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
        if _get_channel_state(_CHANNELS[i]) is _UNALLOCATED_STATE:
            return i
    return None


def _get_unallocated_session_index() -> int | None:
    for i in range(_MAX_SESSIONS_COUNT):
        if (_SESSIONS[i]) is _UNALLOCATED_STATE:
            return i
    return None


def _get_channel_state(channel: ChannelCache) -> int:
    return int.from_bytes(channel.state, "big")


def _get_session_state(session: SessionThpCache) -> int:
    return int.from_bytes(session.state, "big")


def get_next_channel_id() -> bytes:
    global cid_counter
    while True:
        cid_counter += 1
        if cid_counter >= BROADCAST_CHANNEL_ID:
            cid_counter = 1
        if _is_cid_unique():
            break
    return cid_counter.to_bytes(_CHANNEL_ID_LENGTH, "big")


def _is_cid_unique() -> bool:
    global cid_counter
    cid_counter_bytes = cid_counter.to_bytes(_CHANNEL_ID_LENGTH, "big")
    for channel in _CHANNELS:
        if channel.channel_id == cid_counter_bytes:
            return False
    return True


def _get_least_recently_used_item(
    list: list[ChannelCache] | list[SessionThpCache], max_count: int
) -> int:
    global _usage_counter
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


def clear_all_except_one_session_keys(excluded: Tuple[bytes, bytes]) -> None:
    cid, sid = excluded

    for channel in _CHANNELS:
        if channel.channel_id != cid:
            channel.clear()

    for session in _SESSIONS:
        if session.channel_id != cid and session.session_id != sid:
            session.clear()
        else:
            s_last_usage = session.last_usage
            session.clear()
            session.last_usage = s_last_usage
            session.state = bytearray(_SEEDLESS_STATE.to_bytes(1, "big"))
            session.session_id[:] = bytearray(sid)
            session.channel_id[:] = bytearray(cid)
