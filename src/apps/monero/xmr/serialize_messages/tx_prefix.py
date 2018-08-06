from micropython import const

from apps.monero.xmr.serialize.base_types import UInt8, UVarintType
from apps.monero.xmr.serialize.message_types import (
    ContainerType,
    MessageType,
    VariantType,
)
from apps.monero.xmr.serialize_messages.base import ECPublicKey, Hash, KeyImage

_c0 = const(0)
_c1 = const(1)
_c32 = const(32)
_c64 = const(64)


class TxoutToScript(MessageType):
    __slots__ = ("keys", "script")
    VARIANT_CODE = 0x0

    @classmethod
    def f_specs(cls):
        return (("keys", ContainerType, ECPublicKey), ("script", ContainerType, UInt8))


class TxoutToKey(MessageType):
    __slots__ = ("key",)
    VARIANT_CODE = 0x2

    @classmethod
    def f_specs(cls):
        return (("key", ECPublicKey),)


class TxoutToScriptHash(MessageType):
    __slots__ = ("hash",)
    VARIANT_CODE = 0x1

    @classmethod
    def f_specs(cls):
        return (("hash", Hash),)


class TxoutTargetV(VariantType):
    @classmethod
    def f_specs(cls):
        return (
            ("txout_to_script", TxoutToScript),
            ("txout_to_scripthash", TxoutToScriptHash),
            ("txout_to_key", TxoutToKey),
        )


class TxinGen(MessageType):
    __slots__ = ("height",)
    VARIANT_CODE = 0xFF

    @classmethod
    def f_specs(cls):
        return (("height", UVarintType),)


class TxinToKey(MessageType):
    __slots__ = ("amount", "key_offsets", "k_image")
    VARIANT_CODE = 0x2

    @classmethod
    def f_specs(cls):
        return (
            ("amount", UVarintType),
            ("key_offsets", ContainerType, UVarintType),
            ("k_image", KeyImage),
        )


class TxinToScript(MessageType):
    __slots__ = ()
    VARIANT_CODE = _c0


class TxinToScriptHash(MessageType):
    __slots__ = ()
    VARIANT_CODE = _c1


class TxInV(VariantType):
    @classmethod
    def f_specs(cls):
        return (
            ("txin_gen", TxinGen),
            ("txin_to_script", TxinToScript),
            ("txin_to_scripthash", TxinToScriptHash),
            ("txin_to_key", TxinToKey),
        )


class TxOut(MessageType):
    __slots__ = ("amount", "target")

    @classmethod
    def f_specs(cls):
        return (("amount", UVarintType), ("target", TxoutTargetV))
