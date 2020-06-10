from micropython import const

from apps.monero.xmr.serialize.base_types import UVarintType
from apps.monero.xmr.serialize.message_types import ContainerType, MessageType
from apps.monero.xmr.serialize_messages.base import KeyImage


class TxinToKey(MessageType):
    __slots__ = ("amount", "key_offsets", "k_image")
    VARIANT_CODE = const(0x2)

    @classmethod
    def f_specs(cls):
        return (
            ("amount", UVarintType),
            ("key_offsets", ContainerType, UVarintType),
            ("k_image", KeyImage),
        )
