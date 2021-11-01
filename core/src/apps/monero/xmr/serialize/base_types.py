from apps.monero.xmr.serialize.int_serialize import (
    dump_uint,
    dump_uvarint,
    load_uint,
    load_uvarint,
)

if False:
    from trezor.utils import HashWriter


class XmrType:
    pass


class UVarintType(XmrType):
    @staticmethod
    def load(reader) -> int:
        return load_uvarint(reader)

    @staticmethod
    def dump(writer: HashWriter, n: int) -> None:
        return dump_uvarint(writer, n)


class IntType(XmrType):
    WIDTH = 0

    @classmethod
    def load(cls, reader) -> int:
        return load_uint(reader, cls.WIDTH)

    @classmethod
    def dump(cls, writer: HashWriter, n: int) -> None:
        return dump_uint(writer, n, cls.WIDTH)


class UInt8(IntType):
    WIDTH = 1
