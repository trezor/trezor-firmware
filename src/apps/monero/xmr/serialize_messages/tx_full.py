from apps.monero.xmr.serialize.message_types import MessageType
from apps.monero.xmr.serialize_messages.base import ECKey
from apps.monero.xmr.serialize_messages.ct_keys import KeyM


class MgSig(MessageType):
    __slots__ = ("ss", "cc", "II")

    @classmethod
    def f_specs(cls):
        return (("ss", KeyM), ("cc", ECKey))
