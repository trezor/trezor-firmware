from micropython import const
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

    AckCallback = Callable[[], None]

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


# Show "trouble communicating" warning after 2s of "blank" screen (if ButtonRequest is not ACKed)
_UNRESPONSIVE_WARNING_TIMEOUT_MS = const(2000)


async def _waiting_screen(raise_on_cancel: type[Exception] | None) -> None:
    import trezorui_api
    from trezor import TR
    from trezor.ui import Layout

    verb = TR.buttons__abort if raise_on_cancel is not None else TR.buttons__continue

    await loop.sleep(_UNRESPONSIVE_WARNING_TIMEOUT_MS)
    with trezorui_api.show_warning(
        title="",
        description=TR.words__comm_trouble,
        button=verb,
        danger=True,
        allow_cancel=False,
    ) as obj:
        # Block until the user confirmation.
        # Don't use `interact` to avoid cancelling current workflow.
        layout = Layout(obj)
        layout.start()
        # This task doesn't have access to I/O context - see `ButtonRequestHandler.join()`.
        # Therefore, the new layout won't start its own ButtonRequest handler,
        # avoiding interference with the existing layout (the one we are waiting for).
        assert layout.button_request_handler is None
        await layout.get_result()

    if raise_on_cancel:
        raise raise_on_cancel()


class ButtonRequestHandler:
    """Handle button requests and unexpected messages from host."""

    def __init__(self, ctx: Context) -> None:
        from trezor.wire.errors import ActionCancelled

        self.ctx = ctx  # used for communication with the host.

        # will be raised from `self.join()` on user cancellation.
        self.raise_on_cancel: type[ActionCancelled] | None = ActionCancelled

        # Receives ButtonRequest notifications from the active layout,
        # or `None` when the layout is closed.
        self.box: loop.mailbox[ButtonRequest | None] = loop.mailbox()

        # Allows the layout to block until ButtonRequest handling is over,
        # using `join()` method.
        self.is_done: loop.mailbox[None] = loop.mailbox()

        if __debug__:
            # Is there a pending ButtonRequest (still waiting for an ButtonAck)?
            # Used for detecting missing ButtonAck in debug builds.
            self.pending = False

    def put(self, br: ButtonRequest) -> None:
        if __debug__:
            if self.pending:
                from . import FirmwareError

                raise FirmwareError(
                    "button request already pending -- "
                    "don't forget to yield your input flow from time to time ^_^"
                )
            self.pending = True

        # in production, we don't want this to fail, hence replace=True
        self.box.put(br, replace=True)

    async def br_task(self, ack_callback: AckCallback) -> None:
        assert self.is_done.is_empty()
        try:
            await self._handle(ack_callback)
        finally:
            # no pending I/O - mark as done, to unblock `join()`.
            self.is_done.put(None)

    async def join(self) -> None:
        # `br_task()` must be scheduled before joining.

        # notify the handler that no more button requests are expected
        # in production, we don't want this to fail, hence replace=True
        self.box.put(None, replace=True)

        # Wait for the ButtonRequest handler to finish (or user cancellation)
        # `_waiting_screen` layout won't have an I/O context, since it runs in a separate task.
        await loop.race(self.is_done, _waiting_screen(self.raise_on_cancel))

    async def _handle(self, ack_callback: AckCallback) -> None:
        from trezor.messages import ButtonAck

        while True:
            # The following task will raise on any incoming message.
            unexpected_read = self.ctx.read(None)
            br = await loop.race(unexpected_read, self.box)

            # Exit the loop when the layout is done.
            if br is None:
                if __debug__:
                    self.pending = False
                return

            if __debug__:
                log.info(__name__, "ButtonRequest sent: %s", br.name)
            await self.ctx.call(br, ButtonAck)
            if __debug__:
                self.pending = False
                log.info(__name__, "ButtonRequest acked: %s", br.name)
            ack_callback()


class ContinueOnErrors(ButtonRequestHandler):
    """Handle I/O from host, while ignoring errors."""

    def __init__(self, ctx: Context, msg: str) -> None:
        super().__init__(ctx)
        self.raise_on_cancel = None  # continue on user cancellation
        self._prev_handler: ButtonRequestHandler | None = None
        self.msg = msg
        self.ignore = False

    def put(self, br: ButtonRequest) -> None:
        if self.ignore:
            # Stop handling ButtonRequests in case of unexpected error.
            if __debug__:
                log.debug(__name__, "ButtonRequest: skipped %s (%s)", br.code, br.name)
            return

        super().put(br)

    async def join(self) -> None:
        if self.ignore:
            # Stop handling ButtonRequests in case of unexpected error.
            return

        await super().join()

    async def br_task(self, ack_callback: AckCallback) -> None:
        if self.ignore:
            # Stop handling ButtonRequests in case of unexpected error.
            return None

        return await super().br_task(ack_callback)

    async def _handle(self, ack_callback: AckCallback) -> None:
        """Unexpected messages will not cause the handler to fail."""

        from .context import UnexpectedMessageException

        # In case of an unexpected error, stop handling ButtonRequests till the end of this workflow.
        # The host will be ignored, disabling host-side cancellation of this workflow.
        success = False
        try:
            while True:
                try:
                    # Exit the loop when the layout is done.
                    await super(ContinueOnErrors, self)._handle(ack_callback)
                    # All is well, continue handling ButtonRequests.
                    success = True
                    return
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
                except Exception as exc:
                    if __debug__:
                        log.error(__name__, "ButtonRequest: ignored %s", exc)
                        log.exception(__name__, exc)
                    # Stop handling ButtonRequests in case of unexpected error (without failing the flow)
                    return
        finally:
            # Handles GeneratorExit as well (in case of task cancellation).
            self.ignore = not success

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
