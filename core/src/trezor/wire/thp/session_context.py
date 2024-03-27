from storage import cache_thp
from storage.cache_thp import SessionThpCache
from trezor import protobuf

from ..protocol_common import Context
from . import SessionState
from .channel_context import ChannelContext


class SessionContext(Context):
    def __init__(
        self, channel_context: ChannelContext, session_cache: SessionThpCache
    ) -> None:
        if channel_context.channel_id != session_cache.channel_id:
            raise Exception(
                "The session has different channel id than the provided channel context!"
            )
        super().__init__(channel_context.iface, channel_context.channel_id)
        self.channel_context = channel_context
        self.session_cache = session_cache
        self.session_id = int.from_bytes(session_cache.session_id, "big")

    async def write(self, msg: protobuf.MessageType) -> None:
        return await self.channel_context.write(msg, self.session_id)

    @classmethod
    def create_new_session(cls, channel_context: ChannelContext) -> "SessionContext":
        session_cache = cache_thp.get_new_session(channel_context.channel_cache)
        return cls(channel_context, session_cache)

    # ACCESS TO SESSION DATA

    def get_session_state(self) -> SessionState:
        state = int.from_bytes(self.session_cache.state, "big")
        return SessionState(state)

    def set_session_state(self, state: SessionState) -> None:
        self.session_cache.state = bytearray(state.value.to_bytes(1, "big"))

    # Called by channel context

    async def receive_message(self, message_type, encoded_protobuf_message):
        pass  # TODO implement


def load_cached_sessions(channel: ChannelContext) -> dict[int, SessionContext]:  # TODO
    sessions: dict[int, SessionContext] = {}
    cached_sessions = cache_thp.get_all_allocated_sessions()
    for session in cached_sessions:
        if session.channel_id == channel.channel_id:
            sid = int.from_bytes(session.session_id, "big")
            sessions[sid] = SessionContext(channel, session)
    return sessions
