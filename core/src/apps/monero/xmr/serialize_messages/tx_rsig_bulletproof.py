from apps.monero.xmr.serialize.message_types import MessageType
from apps.monero.xmr.serialize_messages.base import ECKey
from apps.monero.xmr.serialize_messages.ct_keys import KeyV


class Bulletproof(MessageType):
    @classmethod
    def f_specs(cls):
        return (
            ("A", ECKey),
            ("S", ECKey),
            ("T1", ECKey),
            ("T2", ECKey),
            ("taux", ECKey),
            ("mu", ECKey),
            ("L", KeyV),
            ("R", KeyV),
            ("a", ECKey),
            ("b", ECKey),
            ("t", ECKey),
        )
