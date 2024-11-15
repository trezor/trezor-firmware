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


class Context:
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
    ) -> protobuf.MessageType: ...

    async def write(self, msg: protobuf.MessageType) -> None: ...

    async def call(
        self,
        msg: protobuf.MessageType,
        expected_type: type[LoadedMessageType],
    ) -> LoadedMessageType:
        assert expected_type.MESSAGE_WIRE_TYPE is not None

        await self.write(msg)
        del msg
        return await self.read((expected_type.MESSAGE_WIRE_TYPE,), expected_type)

    def release(self) -> None:
        pass

    @property
    def cache(self) -> DataCache: ...


class WireError(Exception):
    pass
