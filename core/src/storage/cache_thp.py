import builtins
from micropython import const
from typing import TYPE_CHECKING

from storage.cache_common import DataCache
from trezor import utils

if TYPE_CHECKING:
    from typing import TypeVar

    T = TypeVar("T")

if __debug__:
    from trezor import log

# THP specific constants
_MAX_CHANNELS_COUNT = const(10)
_MAX_SESSIONS_COUNT = const(20)


_CHANNEL_STATE_LENGTH = const(1)
_WIRE_INTERFACE_LENGTH = const(1)
_SESSION_STATE_LENGTH = const(1)
_CHANNEL_ID_LENGTH = const(2)
SESSION_ID_LENGTH = const(1)
BROADCAST_CHANNEL_ID = const(65535)
KEY_LENGTH = const(32)
TAG_LENGTH = const(16)
_UNALLOCATED_STATE = const(0)
MANAGEMENT_SESSION_ID = const(0)


class ConnectionCache(DataCache):
    def __init__(self) -> None:
        self.channel_id = bytearray(_CHANNEL_ID_LENGTH)
        self.last_usage = 0
        super().__init__()

    def clear(self) -> None:
        self.channel_id[:] = b""
        self.last_usage = 0
        super().clear()


class ChannelCache(ConnectionCache):
    def __init__(self) -> None:
        self.host_ephemeral_pubkey = bytearray(KEY_LENGTH)
        self.state = bytearray(_CHANNEL_STATE_LENGTH)
        self.iface = bytearray(1)  # TODO add decoding
        self.sync = 0x80  # can_send_bit | sync_receive_bit | sync_send_bit | rfu(5)
        self.session_id_counter = 0x00
        self.fields = (
            32,  # CHANNEL_HANDSHAKE_HASH
            32,  # CHANNEL_KEY_RECEIVE
            32,  # CHANNEL_KEY_SEND
            8,  # CHANNEL_NONCE_RECEIVE
            8,  # CHANNEL_NONCE_SEND
        )
        super().__init__()

    def clear(self) -> None:
        self.state[:] = bytearray(
            int.to_bytes(0, _CHANNEL_STATE_LENGTH, "big")
        )  # Set state to UNALLOCATED
        # TODO clear all keys
        super().clear()


class SessionThpCache(ConnectionCache):
    def __init__(self) -> None:
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
        self.state[:] = bytearray(int.to_bytes(0, 1, "big"))  # Set state to UNALLOCATED
        self.session_id[:] = b""
        super().clear()


_CHANNELS: list[ChannelCache] = []
_SESSIONS: list[SessionThpCache] = []


def initialize() -> None:
    global _CHANNELS
    global _SESSIONS

    for _ in range(_MAX_CHANNELS_COUNT):
        _CHANNELS.append(ChannelCache())
    for _ in range(_MAX_SESSIONS_COUNT):
        _SESSIONS.append(SessionThpCache())

    for channel in _CHANNELS:
        channel.clear()
    for session in _SESSIONS:
        session.clear()


# First unauthenticated channel will have index 0
_usage_counter = 0

# with this (arbitrary) value=4659, the first allocated channel will have cid=1234 (hex)
cid_counter: int = 4659  # TODO change to random value on start


def get_new_channel(iface: bytes) -> ChannelCache:
    if len(iface) != _WIRE_INTERFACE_LENGTH:
        raise Exception("Invalid WireInterface (encoded) length")

    new_cid = get_next_channel_id()
    index = _get_next_unauthenticated_channel_index()

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


def update_channel_last_used(channel_id):
    for channel in _CHANNELS:
        if channel.channel_id == channel_id:
            channel.last_usage = _get_usage_counter_and_increment()
            return


def update_session_last_used(channel_id, session_id):
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


def get_allocated_sessions(channel_id: bytes) -> list[SessionThpCache]:
    if __debug__:
        from trezor.utils import get_bytes_as_str
    _list: list[SessionThpCache] = []
    for session in _SESSIONS:
        if _get_session_state(session) == _UNALLOCATED_STATE:
            continue
        if session.channel_id != channel_id:
            continue
        _list.append(session)
        if __debug__:
            log.debug(
                __name__,
                "session with channel_id: %s and session_id: %s is in ALLOCATED state",
                get_bytes_as_str(session.channel_id),
                get_bytes_as_str(session.session_id),
            )

    return _list


def set_channel_host_ephemeral_key(channel: ChannelCache, key: bytearray) -> None:
    if len(key) != KEY_LENGTH:
        raise Exception("Invalid key length")
    channel.host_ephemeral_pubkey = key


def get_new_session(channel: ChannelCache):
    new_sid = get_next_session_id(channel)
    index = _get_next_session_index()

    _SESSIONS[index] = SessionThpCache()
    _SESSIONS[index].channel_id[:] = channel.channel_id
    _SESSIONS[index].session_id[:] = new_sid
    _SESSIONS[index].last_usage = _get_usage_counter_and_increment()
    channel.last_usage = (
        _get_usage_counter_and_increment()
    )  # increment also use of the channel so it does not get replaced
    _SESSIONS[index].state[:] = bytearray(
        _UNALLOCATED_STATE.to_bytes(_SESSION_STATE_LENGTH, "big")
    )
    return _SESSIONS[index]


def _get_usage_counter() -> int:
    global _usage_counter
    return _usage_counter


def _get_usage_counter_and_increment() -> int:
    global _usage_counter
    _usage_counter += 1
    return _usage_counter


def _get_next_unauthenticated_channel_index() -> int:
    idx = _get_unallocated_channel_index()
    if idx is not None:
        return idx
    return get_least_recently_used_item(_CHANNELS, max_count=_MAX_CHANNELS_COUNT)


def _get_next_session_index() -> int:
    idx = _get_unallocated_session_index()
    if idx is not None:
        return idx
    return get_least_recently_used_item(_SESSIONS, _MAX_SESSIONS_COUNT)


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


def get_next_session_id(channel: ChannelCache) -> bytes:
    while True:
        if channel.session_id_counter >= 255:
            channel.session_id_counter = 1
        else:
            channel.session_id_counter += 1
        if _is_session_id_unique(channel):
            break
    new_sid = channel.session_id_counter
    return new_sid.to_bytes(SESSION_ID_LENGTH, "big")


def _is_session_id_unique(channel: ChannelCache) -> bool:
    for session in _SESSIONS:
        if session.channel_id == channel.channel_id:
            if session.session_id == channel.session_id_counter:
                return False
    return True


def _is_cid_unique() -> bool:
    for session in _SESSIONS:
        if cid_counter == _get_cid(session):
            return False
    return True


def _get_cid(session: SessionThpCache) -> int:
    return int.from_bytes(session.session_id[2:], "big")


def get_least_recently_used_item(
    list: list[ChannelCache] | list[SessionThpCache], max_count: int
):
    lru_counter = _get_usage_counter()
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


def clear_sessions_with_channel_id(channel_id: bytes):
    for session in _SESSIONS:
        if session.channel_id == channel_id:
            session.clear()


def clear_all() -> None:
    for session in _SESSIONS:
        session.clear()
    for channel in _CHANNELS:
        channel.clear()
