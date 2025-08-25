from typing import TYPE_CHECKING

from storage import cache_thp
from storage.cache_common import InvalidSessionError
from storage.cache_thp import SessionThpCache
from trezor import protobuf
from trezor.wire import message_handler, protocol_common
from trezor.wire.context import UnexpectedMessageException
from trezor.wire.message_handler import failure, handle_single_message

from ..protocol_common import Context, Message
from . import SessionState

if TYPE_CHECKING:
    from typing import Awaitable, Container

    from storage.cache_common import DataCache

    from .channel import Channel

    pass

_EXIT_LOOP = True
_REPEAT_LOOP = False

if __debug__:
    from trezor import log
    from trezor.utils import hexlify_if_bytes


class GenericSessionContext(Context):

    def __init__(self, channel: Channel, session_id: int) -> None:
        super().__init__(channel.iface, channel.channel_id)
        self.channel: Channel = channel
        self.session_id: int = session_id

    async def handle(self, message: Message) -> None:
        if __debug__:
            log.debug(
                __name__,
                "handle - start (channel_id (bytes): %s, session_id: %d)",
                hexlify_if_bytes(self.channel_id),
                self.session_id,
                iface=self.iface,
            )

        while True:
            try:
                await handle_single_message(self, message)
                if __debug__:
                    self.channel._log("session loop is over")
            except protocol_common.WireError as e:
                if __debug__:
                    log.exception(__name__, e, iface=self.iface)
                await self.write(failure(e))
            except UnexpectedMessageException as unexpected:
                # The workflow was interrupted by an unexpected message. We need to
                # process it as if it was a new message...
                message = unexpected.msg
                continue
            except Exception as exc:
                if __debug__:
                    log.exception(__name__, exc, iface=self.iface)
            return

    async def _read_next_message(self) -> Message:
        while True:
            session_id, message = await self.channel.decrypt_message()
            if session_id == self.session_id:
                return message
            if __debug__:
                self.channel._log(
                    "Ignored message for unexpected session", logger=log.warning
                )

    async def read(
        self,
        expected_types: Container[int],
        expected_type: type[protobuf.MessageType] | None = None,
    ) -> protobuf.MessageType:
        if __debug__:
            exp_type: str = str(expected_type)
            if expected_type is not None:
                exp_type = expected_type.MESSAGE_NAME
            log.debug(
                __name__,
                "Read - with expected types %s and expected type %s",
                str(expected_types),
                exp_type,
                iface=self.iface,
            )

        message = await self._read_next_message()
        if message.type not in expected_types:
            if __debug__:
                log.debug(
                    __name__,
                    "EXPECTED TYPES: %s\nRECEIVED TYPE: %s",
                    str(expected_types),
                    str(message.type),
                    iface=self.iface,
                )
            raise UnexpectedMessageException(message)

        if expected_type is None:
            expected_type = protobuf.type_for_wire(
                self.message_type_enum_name, message.type
            )

        return message_handler.wrap_protobuf_load(message.data, expected_type)

    def write(self, msg: protobuf.MessageType) -> Awaitable[None]:
        return self.channel.write(msg, self.session_id)

    def get_session_state(self) -> SessionState: ...


class SeedlessSessionContext(GenericSessionContext):

    def __init__(self, channel_ctx: Channel, session_id: int) -> None:
        super().__init__(channel_ctx, session_id)

    def get_session_state(self) -> SessionState:
        return SessionState.SEEDLESS

    @property
    def cache(self) -> DataCache:
        raise InvalidSessionError


class SessionContext(GenericSessionContext):

    def __init__(self, channel_ctx: Channel, session_cache: SessionThpCache) -> None:
        if channel_ctx.channel_id != session_cache.channel_id:
            raise Exception(
                "The session has different channel id than the provided channel context!"
            )
        session_id = int.from_bytes(session_cache.session_id, "big")
        super().__init__(channel_ctx, session_id)
        self.session_cache = session_cache

    # ACCESS TO SESSION DATA

    def get_session_state(self) -> SessionState:
        from storage.cache_common import SESSION_STATE

        state = self.session_cache.get_int(
            SESSION_STATE, default=SessionState.UNALLOCATED
        )
        return SessionState(state)

    def set_session_state(self, state: SessionState) -> None:
        from storage.cache_common import SESSION_STATE

        self.session_cache.set_int(SESSION_STATE, state)

    def release(self) -> None:
        if self.session_cache is not None:
            cache_thp.clear_session(self.session_cache)

    # ACCESS TO CACHE
    @property
    def cache(self) -> DataCache:
        return self.session_cache
