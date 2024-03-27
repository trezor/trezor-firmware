import builtins
from micropython import const
from typing import TYPE_CHECKING

from storage.cache_common import DataCache, InvalidSessionError
from trezor import utils

if TYPE_CHECKING:
    from typing import TypeVar

    T = TypeVar("T")

# THP specific constants
_MAX_CHANNELS_COUNT = 10
_MAX_SESSIONS_COUNT = const(20)
_MAX_UNAUTHENTICATED_SESSIONS_COUNT = const(5)  # TODO remove


_CHANNEL_STATE_LENGTH = const(1)
_WIRE_INTERFACE_LENGTH = const(1)
_SESSION_STATE_LENGTH = const(1)
_CHANNEL_ID_LENGTH = const(2)
_SESSION_ID_LENGTH = const(1)
BROADCAST_CHANNEL_ID = const(65535)
KEY_LENGTH = const(32)
TAG_LENGTH = const(16)
_UNALLOCATED_STATE = const(0)


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
        self.enc_key = bytearray(KEY_LENGTH)
        self.dec_key = bytearray(KEY_LENGTH)
        self.state = bytearray(_CHANNEL_STATE_LENGTH)
        self.iface = bytearray(1)  # TODO add decoding
        self.sync = 0x80  # can_send_bit | sync_receive_bit | sync_send_bit | rfu(5)
        self.session_id_counter = 0x00
        self.fields = ()
        super().__init__()

    def clear(self) -> None:
        self.state[:] = bytearray(
            int.to_bytes(0, _CHANNEL_STATE_LENGTH, "big")
        )  # Set state to UNALLOCATED
        # TODO clear all sessions that are under this channel
        super().clear()


class SessionThpCache(ConnectionCache):
    def __init__(self) -> None:
        self.session_id = bytearray(_SESSION_ID_LENGTH)
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
                1,  # APP_COMMON_DERIVE_CARDANO
                96,  # APP_CARDANO_ICARUS_SECRET
                96,  # APP_CARDANO_ICARUS_TREZOR_SECRET
                1,  # APP_MONERO_LIVE_REFRESH
            )
        self.sync = 0x80  # can_send_bit | sync_receive_bit | sync_send_bit | rfu(5)
        self.last_usage = 0
        super().__init__()

    def clear(self) -> None:
        self.state[:] = bytearray(int.to_bytes(0, 1, "big"))  # Set state to UNALLOCATED
        self.session_id[:] = b""
        super().clear()


_CHANNELS: list[ChannelCache] = []
_SESSIONS: list[SessionThpCache] = []
_UNAUTHENTICATED_SESSIONS: list[SessionThpCache] = []  # TODO remove/replace


def initialize() -> None:
    global _CHANNELS
    global _SESSIONS
    global _UNAUTHENTICATED_SESSIONS

    for _ in range(_MAX_CHANNELS_COUNT):
        _CHANNELS.append(ChannelCache())
    for _ in range(_MAX_SESSIONS_COUNT):
        _SESSIONS.append(SessionThpCache())

    for _ in range(_MAX_UNAUTHENTICATED_SESSIONS_COUNT):
        _UNAUTHENTICATED_SESSIONS.append(SessionThpCache())

    for channel in _CHANNELS:
        channel.clear()
    for session in _SESSIONS:
        session.clear()

    for session in _UNAUTHENTICATED_SESSIONS:
        session.clear()


initialize()


# THP vars
_next_unauthenicated_session_index: int = 0  # TODO remove

# First unauthenticated channel will have index 0
_is_active_session_authenticated: bool
_active_session_idx: int | None = None
_usage_counter = 0

# with this (arbitrary) value=4659, the first allocated channel will have cid=1234 (hex)
cid_counter: int = 4659  # TODO change to random value on start


def get_new_unauthenticated_channel(iface: bytes) -> ChannelCache:
    if len(iface) != _WIRE_INTERFACE_LENGTH:
        raise Exception("Invalid WireInterface (encoded) length")

    new_cid = get_next_channel_id()
    index = _get_next_unauthenticated_channel_index()

    # clear sessions from replaced channel
    if _get_channel_state(_CHANNELS[index]) != _UNALLOCATED_STATE:
        old_cid = _CHANNELS[index].channel_id
        for session in _SESSIONS:
            if session.channel_id == old_cid:
                session.clear()

    _CHANNELS[index] = ChannelCache()
    _CHANNELS[index].channel_id[:] = new_cid
    _CHANNELS[index].last_usage = _get_usage_counter_and_increment()
    _CHANNELS[index].state[:] = bytearray(
        _UNALLOCATED_STATE.to_bytes(_CHANNEL_STATE_LENGTH, "big")
    )
    _CHANNELS[index].iface[:] = bytearray(iface)
    return _CHANNELS[index]


def get_all_allocated_channels() -> list[ChannelCache]:
    _list: list[ChannelCache] = []
    for channel in _CHANNELS:
        if _get_channel_state(channel) != _UNALLOCATED_STATE:
            _list.append(channel)
    return _list


def get_all_allocated_sessions() -> list[SessionThpCache]:
    _list: list[SessionThpCache] = []
    for session in _SESSIONS:
        if _get_session_state(session) != _UNALLOCATED_STATE:
            _list.append(session)
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
    if channel is None:
        return _UNALLOCATED_STATE
    return int.from_bytes(channel.state, "big")


def _get_session_state(session: SessionThpCache) -> int:
    if session is None:
        return _UNALLOCATED_STATE
    return int.from_bytes(session.state, "big")


def get_active_session_id() -> bytearray | None:
    active_session = get_active_session()

    if active_session is None:
        return None
    return active_session.session_id


def get_active_session() -> SessionThpCache | None:
    if _active_session_idx is None:
        return None
    if _is_active_session_authenticated:
        return _SESSIONS[_active_session_idx]
    return _UNAUTHENTICATED_SESSIONS[_active_session_idx]


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
    return new_sid.to_bytes(_SESSION_ID_LENGTH, "big")


def _is_session_id_unique(channel: ChannelCache) -> bool:
    for session in _SESSIONS:
        if session.channel_id == channel.channel_id:
            if session.session_id == channel.session_id_counter:
                return False
    return True


def _is_cid_unique() -> bool:
    for session in _SESSIONS + _UNAUTHENTICATED_SESSIONS:
        if cid_counter == _get_cid(session):
            return False
    return True


def _get_cid(session: SessionThpCache) -> int:
    return int.from_bytes(session.session_id[2:], "big")


def create_new_unauthenticated_session(session_id: bytes) -> SessionThpCache:
    if len(session_id) != _SESSION_ID_LENGTH:
        raise ValueError(
            "session_id must be X bytes long, where X=", _SESSION_ID_LENGTH
        )
    global _active_session_idx
    global _is_active_session_authenticated
    global _next_unauthenicated_session_index

    i = _next_unauthenicated_session_index
    _UNAUTHENTICATED_SESSIONS[i] = SessionThpCache()
    _UNAUTHENTICATED_SESSIONS[i].session_id = bytearray(session_id)
    _next_unauthenicated_session_index += 1
    if _next_unauthenicated_session_index >= _MAX_UNAUTHENTICATED_SESSIONS_COUNT:
        _next_unauthenicated_session_index = 0

    # Set session as active if and only if there is no active session
    if _active_session_idx is None:
        _active_session_idx = i
        _is_active_session_authenticated = False
    return _UNAUTHENTICATED_SESSIONS[i]


def get_unauth_session_index(unauth_session: SessionThpCache) -> int | None:
    for i in range(_MAX_UNAUTHENTICATED_SESSIONS_COUNT):
        if unauth_session == _UNAUTHENTICATED_SESSIONS[i]:
            return i
    return None


def create_new_auth_session(unauth_session: SessionThpCache) -> SessionThpCache:
    unauth_session_idx = get_unauth_session_index(unauth_session)
    if unauth_session_idx is None:
        raise InvalidSessionError

    # replace least recently used authenticated session by the new session
    new_auth_session_index = get_least_recently_used_authetnicated_session_index()

    _SESSIONS[new_auth_session_index] = _UNAUTHENTICATED_SESSIONS[unauth_session_idx]
    _UNAUTHENTICATED_SESSIONS[unauth_session_idx].clear()

    _SESSIONS[new_auth_session_index].last_usage = _get_usage_counter_and_increment()
    return _SESSIONS[new_auth_session_index]


def get_least_recently_used_authetnicated_session_index() -> int:
    return get_least_recently_used_item(_SESSIONS, _MAX_SESSIONS_COUNT)


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


# The function start_session should not be used in production code. It is present only to assure compatibility with old tests.
def start_session(session_id: bytes | None) -> bytes:  # TODO incomplete
    global _active_session_idx
    global _is_active_session_authenticated

    if session_id is not None:
        if get_active_session_id() == session_id:
            return session_id
        for index in range(_MAX_SESSIONS_COUNT):
            if _SESSIONS[index].session_id == session_id:
                _active_session_idx = index
                _is_active_session_authenticated = True
                return session_id
        for index in range(_MAX_UNAUTHENTICATED_SESSIONS_COUNT):
            if _UNAUTHENTICATED_SESSIONS[index].session_id == session_id:
                _active_session_idx = index
                _is_active_session_authenticated = False
                return session_id

    channel = get_new_unauthenticated_channel(b"\x00")

    new_session_id = get_next_session_id(channel)

    new_session = create_new_unauthenticated_session(new_session_id)

    index = get_unauth_session_index(new_session)
    _active_session_idx = index
    _is_active_session_authenticated = False

    return new_session_id


def start_existing_session(session_id: bytes) -> bytes:
    global _active_session_idx
    global _is_active_session_authenticated

    if session_id is None:
        raise ValueError("session_id cannot be None")
    if get_active_session_id() == session_id:
        return session_id
    for index in range(_MAX_SESSIONS_COUNT):
        if _SESSIONS[index].session_id == session_id:
            _active_session_idx = index
            _is_active_session_authenticated = True
            return session_id
    for index in range(_MAX_UNAUTHENTICATED_SESSIONS_COUNT):
        if _UNAUTHENTICATED_SESSIONS[index].session_id == session_id:
            _active_session_idx = index
            _is_active_session_authenticated = False
            return session_id
    raise ValueError("There is no active session with provided session_id")


def end_current_session() -> None:
    global _active_session_idx
    active_session = get_active_session()
    if active_session is None:
        return
    active_session.clear()
    _active_session_idx = None


def get_int_all_sessions(key: int) -> builtins.set[int]:
    values = builtins.set()
    for session in _SESSIONS:  # Should there be _SESSIONS + _UNAUTHENTICATED_SESSIONS ?
        encoded = session.get(key)
        if encoded is not None:
            values.add(int.from_bytes(encoded, "big"))
    return values


def clear_all() -> None:
    global _active_session_idx
    _active_session_idx = None
    for session in _SESSIONS + _UNAUTHENTICATED_SESSIONS:
        session.clear()
