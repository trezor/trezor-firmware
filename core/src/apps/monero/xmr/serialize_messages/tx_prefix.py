from apps.monero.xmr.serialize.message_types import MessageType


class TxinToKey(MessageType):
    __slots__ = ("amount", "key_offsets", "k_image")

    @classmethod
    def f_specs(cls) -> tuple:
        from apps.monero.xmr.serialize.base_types import UVarintType
        from apps.monero.xmr.serialize.message_types import ContainerType
        from apps.monero.xmr.serialize_messages.base import KeyImage

        return (
            ("amount", UVarintType),
            ("key_offsets", ContainerType, UVarintType),
            ("k_image", KeyImage),
        )
