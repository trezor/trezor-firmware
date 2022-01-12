from typing import TYPE_CHECKING

from apps.monero.xmr.serialize.int_serialize import (
    dump_uint,
    dump_uvarint,
    load_uint,
    load_uvarint,
)

if TYPE_CHECKING:
    from typing import Protocol, TypeVar, Union

    T = TypeVar("T")

    XT = TypeVar("XT", bound="XmrType")
    ST = TypeVar("ST", bound="XmrStructuredType")

    XmrFieldType = Union[
        tuple[str, XT],
        tuple[str, ST, XT],
    ]

    XmrFspec = tuple[XmrFieldType, ...]

    class Writer(Protocol):
        def write(self, data: bytes, /) -> None:
            ...

    class Reader(Protocol):
        def readinto(self, buffer: bytearray | memoryview, /) -> int:
            ...

    class XmrType(Protocol[T]):
        def load(self, reader: Reader, /) -> T:
            ...

        def dump(self, writer: Writer, value: T, /) -> None:
            ...

    class XmrStructuredType(XmrType):
        def f_specs(self) -> XmrFspec:
            ...


class UVarintType:
    @staticmethod
    def load(reader: Reader) -> int:
        return load_uvarint(reader)

    @staticmethod
    def dump(writer: Writer, n: int) -> None:
        return dump_uvarint(writer, n)


class IntType:
    WIDTH = 0

    @classmethod
    def load(cls, reader: Reader) -> int:
        return load_uint(reader, cls.WIDTH)

    @classmethod
    def dump(cls, writer: Writer, n: int):
        return dump_uint(writer, n, cls.WIDTH)


class UInt8(IntType):
    WIDTH = 1
