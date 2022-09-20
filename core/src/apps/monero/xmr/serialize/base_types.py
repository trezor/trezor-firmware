from typing import TYPE_CHECKING

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
        def write(self, __data: bytes) -> None:
            ...

    class Reader(Protocol):
        def readinto(self, __buffer: bytearray | memoryview) -> int:
            ...

    class XmrType(Protocol[T]):
        def load(self, __reader: Reader) -> T:
            ...

        def dump(self, __writer: Writer, __value: T) -> None:
            ...

    class XmrStructuredType(XmrType):
        def f_specs(self) -> XmrFspec:
            ...


class UVarintType:
    @staticmethod
    def load(reader: Reader) -> int:
        from apps.monero.xmr.serialize.int_serialize import load_uvarint

        return load_uvarint(reader)

    @staticmethod
    def dump(writer: Writer, n: int) -> None:
        from apps.monero.xmr.serialize.int_serialize import dump_uvarint

        return dump_uvarint(writer, n)
