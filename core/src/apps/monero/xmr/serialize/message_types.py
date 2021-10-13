from trezor.utils import obj_eq, obj_repr

from apps.monero.xmr.serialize.base_types import XmrType
from apps.monero.xmr.serialize.int_serialize import (
    dump_uint,
    dump_uvarint,
    load_uint,
    load_uvarint,
)


class UnicodeType(XmrType):
    """
    Unicode data in UTF-8 encoding.
    """

    @staticmethod
    def dump(writer, s):
        dump_uvarint(writer, len(s))
        writer.write(bytes(s))

    @staticmethod
    def load(reader):
        ivalue = load_uvarint(reader)
        fvalue = bytearray(ivalue)
        reader.readinto(fvalue)
        return str(fvalue)


class BlobType(XmrType):
    """
    Binary data, represented as bytearray.  BlobType is only a scheme
    descriptor.  Behaves in the same way as primitive types.
    """

    FIX_SIZE = 0
    SIZE = 0

    @classmethod
    def dump(cls, writer, elem: bytes):
        if cls.FIX_SIZE:
            if cls.SIZE != len(elem):
                raise ValueError("Size mismatch")
        else:
            dump_uvarint(writer, len(elem))
        writer.write(elem)

    @classmethod
    def load(cls, reader) -> bytearray:
        if cls.FIX_SIZE:
            size = cls.SIZE
        else:
            size = load_uvarint(reader)
        elem = bytearray(size)
        reader.readinto(elem)
        return elem


class ContainerType(XmrType):
    """
    Array of elements, represented as a list of items.  ContainerType is only a
    scheme descriptor.
    """

    FIX_SIZE = 0
    SIZE = 0
    ELEM_TYPE = None

    @classmethod
    def dump(cls, writer, elems, elem_type=None):
        if elem_type is None:
            elem_type = cls.ELEM_TYPE
        if cls.FIX_SIZE:
            if cls.SIZE != len(elems):
                raise ValueError("Size mismatch")
        else:
            dump_uvarint(writer, len(elems))
        for elem in elems:
            elem_type.dump(writer, elem)

    @classmethod
    def load(cls, reader, elem_type=None):
        if elem_type is None:
            elem_type = cls.ELEM_TYPE
        if cls.FIX_SIZE:
            size = cls.SIZE
        else:
            size = load_uvarint(reader)
        elems = []
        for _ in range(size):
            elem = elem_type.load(reader)
            elems.append(elem)
        return elems


class VariantType(XmrType):
    """
    Union of types, differentiated by variant tags. VariantType is only a scheme
    descriptor.
    """

    @classmethod
    def dump(cls, writer, elem):
        for field in cls.f_specs():
            ftype = field[1]
            if isinstance(elem, ftype):
                break
        else:
            raise ValueError(f"Unrecognized variant: {elem}")

        dump_uint(writer, ftype.VARIANT_CODE, 1)
        ftype.dump(writer, elem)

    @classmethod
    def load(cls, reader):
        tag = load_uint(reader, 1)
        for field in cls.f_specs():
            ftype = field[1]
            if ftype.VARIANT_CODE == tag:
                fvalue = ftype.load(reader)
                break
        else:
            raise ValueError(f"Unknown tag: {tag}")
        return fvalue

    @classmethod
    def f_specs(cls):
        return ()


class MessageType(XmrType):
    """
    Message composed of fields with specific types.
    """

    def __init__(self, **kwargs):
        for kw in kwargs:  # pylint: disable=consider-using-dict-items
            setattr(self, kw, kwargs[kw])

    __eq__ = obj_eq
    __repr__ = obj_repr

    @classmethod
    def dump(cls, writer, msg):
        defs = cls.f_specs()
        for field in defs:
            fname, ftype, *fparams = field
            fvalue = getattr(msg, fname, None)
            ftype.dump(writer, fvalue, *fparams)

    @classmethod
    def load(cls, reader):
        msg = cls()
        defs = cls.f_specs()
        for field in defs:
            fname, ftype, *fparams = field
            fvalue = ftype.load(reader, *fparams)
            setattr(msg, fname, fvalue)
        return msg

    @classmethod
    def f_specs(cls):
        return ()
