from typing import TYPE_CHECKING

from storage.cache_thp import MANAGEMENT_SESSION_ID, SessionThpCache
from trezor import log, loop, protobuf
from trezor.wire import message_handler, protocol_common
from trezor.wire.context import UnexpectedMessageException
from trezor.wire.message_handler import AVOID_RESTARTING_FOR, failure, find_handler

from ..protocol_common import Context, Message
from . import SessionState

if TYPE_CHECKING:
    from typing import Any, Awaitable, Container

    from storage.cache_common import DataCache

    from ..message_handler import HandlerFinder
    from .channel import Channel

    pass

_EXIT_LOOP = True
_REPEAT_LOOP = False

if __debug__:
    from trezor.utils import get_bytes_as_str


class GenericSessionContext(Context):

    def __init__(self, channel: Channel, session_id: int) -> None:
        super().__init__(channel.iface, channel.channel_id)
        self.channel: Channel = channel
        self.session_id: int = session_id
        self.incoming_message = loop.chan()
        self.handler_finder: HandlerFinder = find_handler

    async def handle(self) -> None:
        if __debug__:
            self._handle_debug()

        take = self.incoming_message.take()
        next_message: Message | None = None

        while True:
            try:
                if await self._handle_message(take, next_message):
                    loop.schedule(self.handle())
                    return
            except UnexpectedMessageException as unexpected:
                # The workflow was interrupted by an unexpected message. We need to
                # process it as if it was a new message...
                next_message = unexpected.msg
                continue
            except Exception as exc:
                # Log and try again.
                if __debug__:
                    log.exception(__name__, exc)

    def _handle_debug(self) -> None:
        log.debug(
            __name__,
            "handle - start (channel_id (bytes): %s, session_id: %d)",
            get_bytes_as_str(self.channel_id),
            self.session_id,
        )
        # if is_debug_session:
        #     import apps.debug

        #     apps.debug.DEBUG_CONTEXT = self

    async def _handle_message(
        self,
        take: Awaitable[Any],
        next_message: Message | None,
    ) -> bool:

        try:
            message = await self._get_message(take, next_message)
        except protocol_common.WireError as e:
            if __debug__:
                log.exception(__name__, e)
            await self.write(failure(e))
            return _REPEAT_LOOP

        try:
            await message_handler.handle_single_message(
                self,
                message,
                self.handler_finder,
            )
        except UnexpectedMessageException:
            raise
        except Exception as exc:
            # Log and ignore. The session handler can only exit explicitly in the
            # following finally block.
            if __debug__:
                log.exception(__name__, exc)
        finally:
            # Unload modules imported by the workflow.  Should not raise.
            # This is not done for the debug session because the snapshot taken
            # in a debug session would clear modules which are in use by the
            # workflow running on wire.
            # TODO utils.unimport_end(modules)

            if next_message is None and message.type not in AVOID_RESTARTING_FOR:
                # Shut down the loop if there is no next message waiting.
                return _EXIT_LOOP  # pylint: disable=lost-exception
            return _REPEAT_LOOP  # pylint: disable=lost-exception

    async def _get_message(
        self, take: Awaitable[Any], next_message: Message | None
    ) -> Message:
        if next_message is None:
            # If the previous run did not keep an unprocessed message for us,
            # wait for a new one.
            message: Message = await take
        else:
            # Process the message from previous run.
            message = next_message
            next_message = None
        return message

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
            )
        message: Message = await self.incoming_message.take()
        if message.type not in expected_types:
            if __debug__:
                log.debug(
                    __name__,
                    "EXPECTED TYPES: %s\nRECEIVED TYPE: %s",
                    str(expected_types),
                    str(message.type),
                )
            raise UnexpectedMessageException(message)

        if expected_type is None:
            expected_type = protobuf.type_for_wire(message.type)

        return message_handler.wrap_protobuf_load(message.data, expected_type)

    async def write(self, msg: protobuf.MessageType) -> None:
        return await self.channel.write(msg, self.session_id)

    async def write_force(self, msg: protobuf.MessageType) -> None:
        return await self.channel.write(msg, self.session_id, force=True)

    def get_session_state(self) -> SessionState: ...


class ManagementSessionContext(GenericSessionContext):

    def __init__(
        self, channel_ctx: Channel, session_id: int = MANAGEMENT_SESSION_ID
    ) -> None:
        super().__init__(channel_ctx, session_id)

    def get_session_state(self) -> SessionState:
        return SessionState.MANAGEMENT


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
        state = int.from_bytes(self.session_cache.state, "big")
        return SessionState(state)

    def set_session_state(self, state: SessionState) -> None:
        self.session_cache.state = bytearray(state.to_bytes(1, "big"))

    # ACCESS TO CACHE
    @property
    def cache(self) -> DataCache:
        return self.session_cache
