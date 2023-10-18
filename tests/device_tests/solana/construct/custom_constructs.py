from construct import (
    AdaptationError,
    Adapter,
    Byte,
    Bytes,
    Construct,
    GreedyString,
    If,
    Int64ul,
    Optional,
    PaddedString,
    Prefixed,
    PrefixedArray,
    Struct,
    Validator,
    VarInt,
    this,
)

from trezorlib.tools import b58decode, b58encode


def _find_in_context(context, key: str):
    if key in context:
        return context[key]
    elif context._ is not None:
        return _find_in_context(context._, key)
    else:
        return None


class VersionEncodingAdapter(Adapter):
    def _decode(self, obj: int, context, path) -> str | int:
        if obj & 0x80:
            return obj - 0x80

        raise AdaptationError

    def _encode(self, obj: int, context, path) -> int:
        return obj | 0x80


Version = Optional(VersionEncodingAdapter(Byte))


class CompactU16Validator(Validator):
    def _validate(self, obj: int, context, path) -> bool:
        return obj < 0x1_0000


CompactU16 = CompactU16Validator(VarInt)


def CompactArray(subcon: Construct):
    return PrefixedArray(CompactU16, subcon)


def CompactStruct(*subcons, **subconskw):
    return Prefixed(CompactU16, Struct(*subcons, **subconskw))


class B58Adapter(Adapter):
    def _decode(self, obj: str, context, path) -> str:
        # decode/encode is flipped because we are deserializing ("decoding") by representing ("encoding") the bytes in Base58
        return b58encode(obj)

    def _encode(self, obj: str, context, path) -> bytes:
        # decode/encode is flipped because we are serializing ("encoding") by parsing ("decoding") the Base58 string
        return b58decode(obj)


PublicKey = B58Adapter(Bytes(32))


class HexStringAdapter(Adapter):
    def _decode(self, obj: bytes, context, path) -> str:
        return obj.hex()

    def _encode(self, obj: str, context, path) -> bytes:
        return bytes.fromhex(obj)


Memo = GreedyString("utf8")

String = Struct("length" / Int64ul, "chars" / PaddedString(this.length, "utf-8"))


def OptionalParameter(subcon: Construct):
    return Struct(
        "is_included" / Byte,
        "value" / Optional(If(this.is_included == 1, subcon)),
    )
