from typing import TYPE_CHECKING

from trezor import loop, protobuf

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from trezorio import WireInterface
    from typing import (
        Any,
        Awaitable,
        Callable,
        Container,
        Literal,
        NoReturn,
        TypeVar,
        overload,
    )

    from storage.cache_common import DataCache
    from trezor.messages import ButtonRequest

    LoadedMessageType = TypeVar("LoadedMessageType", bound=protobuf.MessageType)
    T = TypeVar("T")


class Message:
    """
    Encapsulates protobuf encoded message, where
    - `type` is the `WIRE_TYPE` of the message
    - `data` is the protobuf encoded message
    """

    def __init__(
        self,
        message_type: int,
        message_data: AnyBytes,
    ) -> None:
        self.data = message_data
        self.type = message_type


class Context:
    """Wire context.

    Represents communication between the Trezor device and a host within
    a specific session over a particular interface (i.e., wire, debug,
    single Bluetooth connection, etc.).
    """

    channel_id: AnyBytes

    def __init__(
        self,
        iface: WireInterface,
        channel_id: AnyBytes | None = None,
        message_type_enum_name: str = "MessageType",
    ) -> None:
        self.iface: WireInterface = iface
        self.message_type_enum_name = message_type_enum_name
        if channel_id is not None:
            self.channel_id = channel_id
        self.button_request_handler = ButtonRequestHandler(self)

    if TYPE_CHECKING:

        # When `expected_types` is None, any received message is treated as unexpected
        # and an exception is raised after the message is received.
        @overload
        async def read(self, expected_types: Literal[None]) -> NoReturn: ...

        @overload
        async def read(
            self, expected_types: Container[int]
        ) -> protobuf.MessageType: ...

        @overload
        async def read(
            self, expected_types: Container[int], expected_type: type[LoadedMessageType]
        ) -> LoadedMessageType: ...

    async def read(
        self,
        expected_types: Container[int] | None,
        expected_type: type[protobuf.MessageType] | None = None,
    ) -> protobuf.MessageType:
        """Read a message from the wire.

        The read message must be of one of the types specified in `expected_types`.
        If only a single type is expected, it can be passed as `expected_type`,
        to save on having to decode the type code into a protobuf class.
        """
        ...

    def write(self, msg: protobuf.MessageType) -> Awaitable[None]:
        """Write a message to the wire."""
        ...

    async def call(
        self,
        msg: protobuf.MessageType,
        expected_type: type[LoadedMessageType],
    ) -> LoadedMessageType:
        """Write a message to the wire, then await and return the response message."""
        assert expected_type.MESSAGE_WIRE_TYPE is not None

        if __debug__:
            # Check if `expected_type` is in the used `message_type_enum`
            # Test skipped for MESSAGE_WIRE_TYPE == 22 because of "TxAck polymorphism" (PR #1266)
            if expected_type.MESSAGE_WIRE_TYPE != 22:
                protobuf.type_for_wire(
                    self.message_type_enum_name, expected_type.MESSAGE_WIRE_TYPE
                )

        await self.write(msg)
        del msg
        return await self.read((expected_type.MESSAGE_WIRE_TYPE,), expected_type)

    def release(self) -> None:
        """Release resources used by the context, eg. clear context cache."""
        pass

    @property
    def cache(self) -> DataCache:
        """Access to the backing cache of the context, if the context has any."""
        ...


class ButtonRequestHandler:
    """Handle button requests and unexpected messages from host."""

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

    async def handle(
        self,
        button_requests: loop.mailbox[ButtonRequest | None],
        ack_callback: Callable[[], None] | None,
    ) -> None:
        from trezor.messages import ButtonAck

        while True:
            # The following task will raise on any incoming message.
            unexpected_read = self.ctx.read(None)
            br = await loop.race(unexpected_read, button_requests)

            # Exit the loop when the layout is done.
            if br is None:
                return

            if __debug__:
                log.info(__name__, "ButtonRequest sent: %s", br.name)
            await self.ctx.call(br, ButtonAck)
            if __debug__:
                log.info(__name__, "ButtonRequest acked: %s", br.name)
            if ack_callback is not None:
                ack_callback()


class ContinueOnErrors(ButtonRequestHandler):
    """Handle I/O from host, while ignoring errors."""

    def __init__(self, ctx: Context, msg: str) -> None:
        super().__init__(ctx)
        self._prev_handler: ButtonRequestHandler | None = None
        self.msg = msg

    async def handle(
        self,
        button_requests: loop.mailbox[ButtonRequest | None],
        ack_callback: Callable[[], None] | None,
    ) -> None:
        """Unexpected messages will not cause the handler to fail."""
        from .context import UnexpectedMessageException

        while True:
            try:
                # Exit the loop when the layout is done.
                return await super().handle(button_requests, ack_callback)
            except UnexpectedMessageException as exc:
                # in case of THP channel preemption, `msg` is not set.
                # TRANSPORT_BUSY error has been already sent by `InterfaceContext.handle_packet()`.
                if exc.msg:
                    from trezor.enums import FailureType
                    from trezor.messages import Failure

                    # notify the host that the device cannot be preempted
                    await self.ctx.write(
                        Failure(code=FailureType.InProgress, message=self.msg)
                    )
                # continue receiving messages

    def __enter__(self) -> None:
        assert self._prev_handler is None
        self._prev_handler = self.ctx.button_request_handler
        self.ctx.button_request_handler = self

    def __exit__(self, exc_type: Any, exc_val: Any, tb: Any) -> None:
        assert self._prev_handler is not None
        self.ctx.button_request_handler = self._prev_handler
        self._prev_handler = None


class WireError(Exception):
    pass
