from micropython import const

from apps.monero.xmr.serialize.message_types import ContainerType, MessageType
from apps.monero.xmr.serialize_messages.base import ECKey

_c0 = const(0)


class KeyV(ContainerType):
    FIX_SIZE = _c0
    ELEM_TYPE = ECKey


class KeyM(ContainerType):
    FIX_SIZE = _c0
    ELEM_TYPE = KeyV


class CtKey(MessageType):
    __slots__ = ("dest", "mask")

    @classmethod
    def f_specs(cls):
        return (("dest", ECKey), ("mask", ECKey))
