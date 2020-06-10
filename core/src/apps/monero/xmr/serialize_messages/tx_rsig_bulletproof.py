from micropython import const

from apps.monero.xmr.serialize.message_types import ContainerType, MessageType
from apps.monero.xmr.serialize_messages.base import ECKey


class _KeyV(ContainerType):
    FIX_SIZE = const(0)
    ELEM_TYPE = ECKey


class Bulletproof(MessageType):
    __slots__ = ("A", "S", "T1", "T2", "taux", "mu", "L", "R", "a", "b", "t")

    @classmethod
    def f_specs(cls):
        return (
            ("A", ECKey),
            ("S", ECKey),
            ("T1", ECKey),
            ("T2", ECKey),
            ("taux", ECKey),
            ("mu", ECKey),
            ("L", _KeyV),
            ("R", _KeyV),
            ("a", ECKey),
            ("b", ECKey),
            ("t", ECKey),
        )
