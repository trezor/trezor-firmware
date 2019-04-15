from apps.monero.xmr.serialize.message_types import MessageType


class EcdhTuple(MessageType):
    __slots__ = ("mask", "amount")
