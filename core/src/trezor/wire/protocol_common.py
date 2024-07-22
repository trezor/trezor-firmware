from typing import TYPE_CHECKING

from trezor import protobuf

if TYPE_CHECKING:
    from trezorio import WireInterface
    from typing import Container, TypeVar, overload

    from storage.cache_common import DataCache

    LoadedMessageType = TypeVar("LoadedMessageType", bound=protobuf.MessageType)
    T = TypeVar("T")


class Message:

    def __init__(
        self,
        message_type: int,
        message_data: bytes,
    ) -> None:
        self.data = message_data
        self.type = message_type

    def to_bytes(self):
        return self.type.to_bytes(2, "big") + self.data


class Context:
    def __init__(self, iface: WireInterface, channel_id: bytes) -> None:
        self.iface: WireInterface = iface
        self.channel_id: bytes = channel_id

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
    ) -> protobuf.MessageType: ...

    async def write(self, msg: protobuf.MessageType) -> None: ...

    async def write_force(self, msg: protobuf.MessageType) -> None:
        await self.write(msg)

    async def call(
        self,
        msg: protobuf.MessageType,
        expected_type: type[LoadedMessageType],
    ) -> LoadedMessageType:
        assert expected_type.MESSAGE_WIRE_TYPE is not None

        await self.write(msg)
        del msg
        return await self.read((expected_type.MESSAGE_WIRE_TYPE,), expected_type)

    @property
    def cache(self) -> DataCache: ...


class WireError(Exception):
    pass
