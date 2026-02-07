from typing import TYPE_CHECKING

from trezor import protobuf

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from trezorio import WireInterface
    from typing import Any, Awaitable, Container, NoReturn, TypeVar, overload

    from storage.cache_common import DataCache
    from trezor import loop

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


class UnexpectedHandler:
    """Create a task for handling unexpected messages."""

    def __init__(self, ctx: "Context") -> None:
        self.ctx = ctx

    def create(self) -> loop.Task[NoReturn]: ...

    def __enter__(self) -> None:
        assert self.ctx._unexpected_handler is None
        self.ctx._unexpected_handler = self

    def __exit__(self, _exc_type: Any, _exc_val: Any, _tb: Any) -> None:
        assert self.ctx._unexpected_handler is self
        self.ctx._unexpected_handler = None


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
        # set via `UnexpectedHandler` context manager
        self._unexpected_handler: UnexpectedHandler | None = None

    if TYPE_CHECKING:

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
        expected_types: Container[int],
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

    def create_unexpected_handler(self) -> loop.Task[NoReturn]:
        if self._unexpected_handler is not None:
            return self._unexpected_handler.create()

        async def _task() -> NoReturn:
            """Default unexpected message handler - cancels current workflow."""
            await self.read(expected_types=())
            assert False  # the above read will always raise

        return _task()

    def release(self) -> None:
        """Release resources used by the context, eg. clear context cache."""
        pass

    @property
    def cache(self) -> DataCache:
        """Access to the backing cache of the context, if the context has any."""
        ...


class WireError(Exception):
    pass
