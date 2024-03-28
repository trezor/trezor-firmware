from typing import TYPE_CHECKING  # pyright: ignore[reportShadowedImports]

from storage import cache_thp
from storage.cache_thp import SessionThpCache
from trezor import loop, protobuf
from trezor.wire import message_handler

from ..protocol_common import Context, MessageWithType
from . import SessionState
from .channel import Channel

if TYPE_CHECKING:
    from typing import Container  # pyright: ignore[reportShadowedImports]

    pass


class UnexpectedMessageWithType(Exception):
    def __init__(self, msg: MessageWithType) -> None:
        super().__init__()
        self.msg = msg


class SessionContext(Context):
    def __init__(self, channel: Channel, session_cache: SessionThpCache) -> None:
        if channel.channel_id != session_cache.channel_id:
            raise Exception(
                "The session has different channel id than the provided channel context!"
            )
        super().__init__(channel.iface, channel.channel_id)
        self.channel_context = channel
        self.session_cache = session_cache
        self.session_id = int.from_bytes(session_cache.session_id, "big")
        self.incoming_message = loop.chan()

    @classmethod
    def create_new_session(cls, channel_context: Channel) -> "SessionContext":
        session_cache = cache_thp.get_new_session(channel_context.channel_cache)
        return cls(channel_context, session_cache)

    async def handle(self) -> None:
        take = self.incoming_message.take()
        while True:
            message = await take
            print(message)
            # TODO continue similarly to handle_session function in wire.__init__

    async def read(
        self,
        expected_types: Container[int],
        expected_type: type[protobuf.MessageType] | None = None,
    ) -> protobuf.MessageType:

        message: MessageWithType = await self.incoming_message.take()
        if message.type not in expected_types:
            raise UnexpectedMessageWithType(message)

        if expected_type is None:
            expected_type = protobuf.type_for_wire(message.type)

        return message_handler.wrap_protobuf_load(message.data, expected_type)

    async def write(self, msg: protobuf.MessageType) -> None:
        return await self.channel_context.write(msg, self.session_id)

    # ACCESS TO SESSION DATA

    def get_session_state(self) -> SessionState:
        state = int.from_bytes(self.session_cache.state, "big")
        return SessionState(state)

    def set_session_state(self, state: SessionState) -> None:
        self.session_cache.state = bytearray(state.value.to_bytes(1, "big"))

    # Called by channel context

    async def receive_message(self, message_type, encoded_protobuf_message):
        pass  # TODO implement


def load_cached_sessions(channel: Channel) -> dict[int, SessionContext]:  # TODO
    sessions: dict[int, SessionContext] = {}
    cached_sessions = cache_thp.get_all_allocated_sessions()
    for session in cached_sessions:
        if session.channel_id == channel.channel_id:
            sid = int.from_bytes(session.session_id, "big")
            sessions[sid] = SessionContext(channel, session)
    return sessions
