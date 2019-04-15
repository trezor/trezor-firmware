from apps.monero.xmr.serialize.int_serialize import (
    dump_uint,
    dump_uvarint,
    load_uint,
    load_uvarint,
)


class XmrType:
    pass


class UVarintType(XmrType):
    @staticmethod
    def load(reader) -> int:
        return load_uvarint(reader)

    @staticmethod
    def dump(writer, n: int):
        return dump_uvarint(writer, n)


class IntType(XmrType):
    WIDTH = 0

    @classmethod
    def load(cls, reader) -> int:
        return load_uint(reader, cls.WIDTH)

    @classmethod
    def dump(cls, writer, n: int):
        return dump_uint(writer, n, cls.WIDTH)


class UInt8(IntType):
    WIDTH = 1
