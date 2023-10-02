import io

from base58 import b58decode
from construct import (
    Construct,
    Int32ul,
    ListContainer,
    PaddedString,
    Padding,
    Struct,
    Subconstruct,
    this,
)


def _find_in_context(context, key):
    if key in context:
        return context[key]
    elif context._ is not None:
        return _find_in_context(context._, key)
    else:
        return None


class Version(Construct):
    def _build(self, obj, stream, context, path):
        if obj != "legacy":
            stream.write(bytes([obj | 0x80]))

        return obj


class CompactU16(Construct):
    def _build(self, obj, stream, context, path):
        value = obj
        while True:
            B = value & 0x7F
            value >>= 7
            if value == 0:
                stream.write(bytes([B]))
                break

            stream.write(bytes([B | 0x80]))

        return obj


class PublicKey(Construct):
    def _build(self, obj, stream, context, path):
        stream.write(b58decode(obj))
        return obj


class CompactArray(Subconstruct):
    def _build(self, obj, stream, context, path):
        CompactU16()._build(len(obj), stream, context, path)

        retlist = ListContainer()
        for i, e in enumerate(obj):
            context._index = i
            retlist.append(self.subcon._build(e, stream, context, path))

        return retlist


class InstructionProgramId(Construct):
    def _build(self, obj, stream, context, path):
        program_index = context._["accounts"].index(obj)
        stream.write(bytes([program_index]))
        return obj


class Accounts(Struct):
    def _build(self, obj, stream, context, path):
        CompactU16()._build(len(obj), stream, context, path)
        super()._build(obj, stream, context, path)
        return obj


class InstructionData(Struct):
    def _build(self, obj, stream, context, path):
        size_stream = io.BytesIO()
        super()._build(obj, size_stream, context, path)
        size = len(size_stream.getvalue())

        CompactU16()._build(size, stream, context, path)
        super()._build(obj, stream, context, path)

        return obj


class InstructionId(Construct):
    def _build(self, obj, stream, context, path):
        instruction_id_formats = _find_in_context(context, "instruction_id_formats")
        program_id = _find_in_context(context, "program_id")

        instruction_id_format = instruction_id_formats[program_id]

        if obj == 0 and not instruction_id_format["is_included_if_zero"]:
            return obj

        length = instruction_id_format["length"]
        if length == 0:
            return obj
        elif length == 1:
            stream.write(bytes([obj]))
        elif length == 4:
            Int32ul._build(obj, stream, context, path)
        else:
            raise ValueError("Invalid instruction ID length")

        return obj


class AccountReference(Construct):
    def _build(self, obj, stream, context, path):
        if obj.startswith("LUT"):
            split_account = obj.split("-")
            lut_index = int(split_account[1])
            lut_account_index = int(split_account[2])

            accounts = _find_in_context(context, "accounts")
            luts = _find_in_context(context, "luts")

            account_index = len(accounts)
            for i, lut in enumerate(luts):
                if i == lut_index:
                    account_index += lut_account_index
                    break

                account_index += len(lut["readwrite"])
                account_index += len(lut["readonly"])
        else:
            accounts = _find_in_context(context, "accounts")
            account_index = accounts.index(obj)

        stream.write(bytes([account_index]))

        return obj


class Memo(Construct):
    def _build(self, obj, stream, context, path):
        stream.write(obj.encode("utf-8"))
        return obj


_STRING = Struct(
    "length" / Int32ul, Padding(4), "chars" / PaddedString(this.length, "utf-8")
)
