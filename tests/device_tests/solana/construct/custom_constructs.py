from base58 import b58decode, b58encode
from construct import (
    Adapter,
    Bytes,
    Construct,
    GreedyBytes,
    GreedyString,
    Int64ul,
    PaddedString,
    Prefixed,
    PrefixedArray,
    Struct,
    Validator,
    VarInt,
    this,
)


def _find_in_context(context, key):
    if key in context:
        return context[key]
    elif context._ is not None:
        return _find_in_context(context._, key)
    else:
        return None


class VersionAdapter(Adapter):
    def _decode(self, obj, context, path):
        if obj & 0x80:
            return obj - 0x80

        return "legacy"

    def _encode(self, obj, context, path):
        if obj != "legacy":
            return bytes([obj | 0x80])

        return bytes()


Version = VersionAdapter(GreedyBytes)


class CompactU16Validator(Validator):
    def _validate(self, obj, context, path):
        return obj < 0x1_0000


CompactU16 = CompactU16Validator(VarInt)


def CompactArray(subcon: Construct):
    return PrefixedArray(CompactU16, subcon)


def CompactStruct(*subcons, **subconskw):
    return Prefixed(CompactU16, Struct(*subcons, **subconskw))


class B58Adapter(Adapter):
    def _decode(self, obj, context, path):
        # decode/encode is flipped because we are deserializing ("decoding") by representing ("encoding") the bytes in Base58
        return b58encode(obj)

    def _encode(self, obj, context, path):
        # decode/encode is flipped because we are serializing ("encoding") by parsing ("decoding") the Base58 string
        return b58decode(obj)


PublicKey = B58Adapter(Bytes(32))


class InstructionIdAdapter(Adapter):
    def _decode(self, obj, context, path):
        return int.from_bytes(obj, "little")

    def _encode(self, obj, context, path):
        instruction_id_formats = _find_in_context(context, "instruction_id_formats")
        program_id = _find_in_context(context, "program_id")

        instruction_id_format = instruction_id_formats[program_id]

        if obj == 0 and not instruction_id_format["is_included_if_zero"]:
            return bytes()

        length = instruction_id_format["length"]
        return obj.to_bytes(length, "little")


InstructionId = InstructionIdAdapter(GreedyBytes)

Memo = GreedyString("utf8")

String = Struct("length" / Int64ul, "chars" / PaddedString(this.length, "utf-8"))
