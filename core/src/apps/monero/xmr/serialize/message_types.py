from typing import TYPE_CHECKING

from trezor.utils import obj_eq, obj_repr

from apps.monero.xmr.serialize.int_serialize import dump_uvarint, load_uvarint

if TYPE_CHECKING:
    from typing import Generic, TypeVar

    from .base_types import Reader, Writer, XmrFspec, XmrType

    T = TypeVar("T", bound=XmrType)
    MT = TypeVar("MT", bound="MessageType")

else:
    Generic = XmrType = [object]
    T = 0


class BlobType:
    """
    Binary data, represented as bytearray.  BlobType is only a scheme
    descriptor.  Behaves in the same way as primitive types.
    """

    FIX_SIZE = 0
    SIZE = 0

    @classmethod
    def dump(cls, writer: Writer, elem: bytes) -> None:
        if cls.FIX_SIZE:
            if cls.SIZE != len(elem):
                raise ValueError("Size mismatch")
        else:
            dump_uvarint(writer, len(elem))
        writer.write(elem)

    @classmethod
    def load(cls, reader: Reader) -> bytes:
        if cls.FIX_SIZE:
            size = cls.SIZE
        else:
            size = load_uvarint(reader)
        elem = bytearray(size)
        reader.readinto(elem)
        return elem


class ContainerType(Generic[T]):
    """
    Array of elements, represented as a list of items.  ContainerType is only a
    scheme descriptor.
    """

    FIX_SIZE = 0
    SIZE = 0
    ELEM_TYPE: XmrType[T]

    @classmethod
    def dump(
        cls, writer: Writer, elems: list[T], elem_type: XmrType[T] | None = None
    ) -> None:
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
    def load(cls, reader: Reader, elem_type: XmrType[T] | None = None) -> list[T]:
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


class MessageType:
    """
    Message composed of fields with specific types.
    """

    def __init__(self, **kwargs):
        for kw in kwargs:  # pylint: disable=consider-using-dict-items
            setattr(self, kw, kwargs[kw])

    __eq__ = obj_eq
    __repr__ = obj_repr

    @classmethod
    def dump(cls: type[MT], writer: Writer, msg: MT) -> None:
        defs = cls.f_specs()
        for field in defs:
            fname, ftype, *fparams = field
            fvalue = getattr(msg, fname, None)
            ftype.dump(writer, fvalue, *fparams)

    @classmethod
    def load(cls: type[MT], reader: Reader) -> MT:
        msg = cls()
        defs = cls.f_specs()
        for field in defs:
            fname, ftype, *fparams = field
            fvalue = ftype.load(reader, *fparams)
            setattr(msg, fname, fvalue)
        return msg

    @classmethod
    def f_specs(cls) -> XmrFspec:
        return ()
