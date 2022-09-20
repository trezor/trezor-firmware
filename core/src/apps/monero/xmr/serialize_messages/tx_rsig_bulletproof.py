from typing import TYPE_CHECKING

from apps.monero.xmr.serialize.message_types import ContainerType, MessageType
from apps.monero.xmr.serialize_messages.base import ECKey

if TYPE_CHECKING:
    from ..serialize.base_types import XmrType


class _KeyV(ContainerType):
    FIX_SIZE = 0
    ELEM_TYPE: XmrType[bytes] = ECKey


class BulletproofPlus(MessageType):
    __slots__ = ("A", "A1", "B", "r1", "s1", "d1", "V", "L", "R")

    @classmethod
    def f_specs(cls) -> tuple:
        return (
            ("A", ECKey),
            ("A1", ECKey),
            ("B", ECKey),
            ("r1", ECKey),
            ("s1", ECKey),
            ("d1", ECKey),
            ("L", _KeyV),
            ("R", _KeyV),
        )
