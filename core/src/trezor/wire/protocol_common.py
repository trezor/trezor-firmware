from typing import TYPE_CHECKING

from trezor import protobuf

if TYPE_CHECKING:
    from trezorio import WireInterface
    from typing import Container, TypeVar, overload

    from storage.cache_common import DataCache

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
        message_data: bytes,
    ) -> None:
        self.data = message_data
        self.type = message_type


class Context:
    """Wire context.

    Represents communication between the Trezor device and a host within
    a specific session over a particular interface (i.e., wire, debug,
    single Bluetooth connection, etc.).
    """

    channel_id: bytes

    def __init__(self, iface: WireInterface, channel_id: bytes | None = None) -> None:
        self.iface: WireInterface = iface
        if channel_id is not None:
            self.channel_id = channel_id

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

    async def write(self, msg: protobuf.MessageType) -> None:
        """Write a message to the wire."""
        ...

    async def call(
        self,
        msg: protobuf.MessageType,
        expected_type: type[LoadedMessageType],
    ) -> LoadedMessageType:
        """Write a message to the wire, then await and return the response message."""
        assert expected_type.MESSAGE_WIRE_TYPE is not None

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


class WireError(Exception):
    pass
