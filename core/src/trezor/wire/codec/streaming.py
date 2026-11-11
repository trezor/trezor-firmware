"""Codec-v1 protobuf I/O using one private USB report, never a message buffer.

Only final protobuf field values are allocated. In particular, a 256-hop proof is
not first reassembled into a second 9 kB byte string. Application proof objects
still have their normal cost; the wire does not borrow the wallet's memory.
"""

from micropython import const
from struct import pack_into, unpack_from
from typing import TYPE_CHECKING

from trezor import io, loop, protobuf, utils
from trezor.wire import DataError

if TYPE_CHECKING:
    from collections.abc import Container
    from typing import TypeVar

    from trezor.wire import WireInterface

    LoadedMessageType = TypeVar("LoadedMessageType", bound=protobuf.MessageType)

REPORT_SIZE = const(64)
MAX_MESSAGE = const(65536)
MAX_BYTES_FIELD = const(8192)
MAX_REPEATED = const(256)
MAX_DEPTH = const(16)
CONTINUATION_TIMEOUT_MS = const(500)


class StreamCodec:
    def __init__(self, iface: WireInterface) -> None:
        if iface.RX_PACKET_LEN != REPORT_SIZE or iface.TX_PACKET_LEN != REPORT_SIZE:
            raise ValueError("WARD requires 64-byte reports")
        self.iface = iface
        self.report = bytearray(REPORT_SIZE)
        self.position = 0
        self.offset = REPORT_SIZE
        self.length = 0

    async def _report(self, continuation: bool = False) -> None:
        read = loop.wait(self.iface.iface_num() | io.POLL_READ)
        if continuation:
            result = await loop.race(read, loop.sleep(CONTINUATION_TIMEOUT_MS))
        else:
            result = await read
        if result != REPORT_SIZE:
            raise DataError("WARD truncated report or continuation timeout")
        if self.iface.read(self.report, 0) != REPORT_SIZE:
            raise DataError("WARD short report")
        if self.report[0] != 63:
            raise DataError("WARD invalid report marker")
        self.offset = 1

    async def header(self) -> int:
        await self._report()
        if self.report[1] != 35 or self.report[2] != 35:
            raise DataError("WARD invalid message header")
        kind, length = unpack_from(">HL", self.report, 3)
        if length > MAX_MESSAGE:
            raise DataError("WARD message too large")
        self.offset = 9
        self.position = 0
        self.length = length
        return kind

    async def byte(self, end: int) -> int:
        if self.position >= end:
            raise DataError("WARD truncated field")
        if self.offset == REPORT_SIZE:
            await self._report(True)
        result = self.report[self.offset]
        self.offset += 1
        self.position += 1
        return result

    async def varint(self, end: int) -> int:
        value = 0
        for shift in range(0, 70, 7):
            byte = await self.byte(end)
            if shift == 63 and byte > 1:
                raise DataError("WARD varint overflow")
            value |= (byte & 127) << shift
            if not byte & 128:
                return value
        raise DataError("WARD invalid varint")

    async def bytes(
        self, length: int, end: int, discard: bool = False
    ) -> bytearray | None:
        if length > end - self.position:
            raise DataError("WARD field crosses message boundary")
        if not discard and length > MAX_BYTES_FIELD:
            raise DataError("WARD bytes field too large")
        value = None if discard else bytearray(length)
        written = 0
        while written < length:
            if self.offset == REPORT_SIZE:
                await self._report(True)
            count = min(length - written, REPORT_SIZE - self.offset)
            if value is not None:
                utils.memcpy(value, written, self.report, self.offset, count)
            self.position += count
            self.offset += count
            written += count
        return value

    async def message(
        self, definition: type[LoadedMessageType], end: int, depth: int = 0
    ) -> LoadedMessageType:
        if depth >= MAX_DEPTH:
            raise DataError("WARD nesting too deep")
        values = {}
        # Cache just this message's encountered fields, not all protocol definitions.
        schema = {}
        while self.position < end:
            key = await self.varint(end)
            tag, wire = key >> 3, key & 7
            if not 0 < tag < 256 or wire not in (0, 2):
                raise DataError("WARD invalid field")
            if tag not in schema:
                schema[tag] = protobuf.field_info(definition, tag)
            field = schema[tag]
            if field is None:
                size = await self.varint(end)
                if wire == 2:
                    await self.bytes(size, end, True)
                continue
            name, kind, repeated, nested = field
            if wire != (2 if kind in (5, 6, 8) else 0):
                raise DataError("WARD incorrect field wire type")
            if not repeated and name in values:
                raise DataError("WARD duplicate field")
            if wire == 0:
                value = await self.varint(end)
                if kind in (0, 1, 7) and value > 0xFFFFFFFF:
                    raise DataError("WARD integer overflow")
                if kind in (1, 3):
                    value = (value >> 1) ^ -(value & 1)
                elif kind == 4:
                    value = bool(value)
                elif kind == 7 and value not in nested:
                    raise DataError("WARD invalid enum")
            else:
                size = await self.varint(end)
                if size > end - self.position:
                    raise DataError("WARD nested message exceeds boundary")
                if kind == 8:
                    value = await self.message(nested, self.position + size, depth + 1)
                else:
                    if name == "proof" and size != 34:
                        raise DataError("WARD proof element must be 34 bytes")
                    value = await self.bytes(size, end)
                    assert value is not None
                    if kind == 6:
                        value = value.decode()
                    elif size <= 64:
                        value = bytes(value)
            if repeated:
                if name not in values:
                    values[name] = []
                if len(values[name]) >= MAX_REPEATED:
                    raise DataError("WARD too many repeated fields")
                values[name].append(value)
            else:
                values[name] = value
        return definition(**values)

    async def read(self, expected: Container[int]) -> protobuf.MessageType:
        kind = await self.header()
        if kind not in expected:
            raise DataError("WARD unexpected service reply")
        definition = protobuf.type_for_wire("MessageType", kind)
        return await self.message(definition, self.length)

    async def write(self, message: protobuf.MessageType) -> None:
        size = protobuf.encoded_length(message)
        if size > MAX_MESSAGE:
            raise DataError("WARD outgoing message too large")
        offset = 9
        sent = 0
        pack_into(">BBBHL", self.report, 0, 63, 35, 35, message.MESSAGE_WIRE_TYPE, size)
        while True:
            count = protobuf.encode_range(
                memoryview(self.report)[offset:], message, sent
            )
            sent += count
            # Clear the unused tail; no bytes from a previous message leave the device.
            for i in range(offset + count, REPORT_SIZE):
                self.report[i] = 0
            while True:
                await loop.wait(self.iface.iface_num() | io.POLL_WRITE)
                written = self.iface.write(self.report)
                if written == REPORT_SIZE:
                    break
                if written != 0:
                    raise DataError("WARD short write")
            if sent >= size:
                break
            self.report[0] = 63
            offset = 1
