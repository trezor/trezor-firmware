from ubinascii import unhexlify

from trezor import wire

from .. import writer
from . import builder, opcode


class ParamStruct:
    """
    Special struct for smart contract argument passing
    """

    def __init__(self, arr: list):
        self.arr = arr


def build_native_call(func_name: str, params: list, contract: bytes) -> bytes:
    """
    Builds native contract call
    """
    ret = bytearray()

    _write_native_code_script(ret, params)
    builder.write_push_bytes(ret, func_name.encode())
    builder.write_push_bytes(ret, contract)
    builder.write_push_int(ret, 0)
    writer.write_byte(ret, opcode.SYSCALL)
    builder.write_push_bytes(ret, b"Ontology.Native.Invoke")

    return ret


def _write_native_code_script(ret: bytearray, arr: list) -> None:
    """
    Writes native code script from supplied data
    """
    for val in reversed(arr):
        if isinstance(val, (bytes, bytearray)):
            builder.write_push_bytes(ret, val)

        elif isinstance(val, bool):
            builder.write_push_bool(ret, val)

        elif isinstance(val, int):
            builder.write_push_int(ret, val)

        elif isinstance(val, ParamStruct):
            builder.write_push_int(ret, 0)
            writer.write_byte(ret, opcode.NEWSTRUCT)
            writer.write_byte(ret, opcode.TOALTSTACK)

            for v in val.arr:
                _write_code_param_script(ret, v)
                writer.write_byte(ret, opcode.DUPFROMALTSTACK)
                writer.write_byte(ret, opcode.SWAP)
                writer.write_byte(ret, opcode.APPEND)

            writer.write_byte(ret, opcode.FROMALTSTACK)

        elif isinstance(val, list) and is_typed_list(val, ParamStruct):
            builder.write_push_int(ret, 0)
            writer.write_byte(ret, opcode.NEWSTRUCT)
            writer.write_byte(ret, opcode.TOALTSTACK)

            for s in val:
                _write_code_param_script(ret, s)

            writer.write_byte(ret, opcode.FROMALTSTACK)
            builder.write_push_int(ret, len(val))
            writer.write_byte(ret, opcode.PACK)

        elif isinstance(val, list):
            print("array")
            _write_native_code_script(ret, val)
            builder.write_push_int(ret, len(val))
            writer.write_byte(ret, opcode.PACK)

        else:
            raise wire.DataError("Invalid param type")


def _write_code_param_script(ret: bytearray, obj) -> None:
    """
    Writes native code param script from supplied data
    """
    if isinstance(obj, str):
        builder.write_push_bytes(ret, unhexlify(obj))

    elif isinstance(obj, (bytes, bytearray)):
        builder.write_push_bytes(ret, obj)

    elif isinstance(obj, bool):
        builder.write_push_bool(ret, obj)

    elif isinstance(obj, int):
        builder.write_push_int(ret, obj)

    elif isinstance(obj, ParamStruct):
        for v in obj.arr:
            _write_code_param_script(ret, v)
            writer.write_byte(ret, opcode.DUPFROMALTSTACK)
            writer.write_byte(ret, opcode.SWAP)
            writer.write_byte(ret, opcode.APPEND)
    else:
        raise wire.DataError("Invalid param type")


def is_typed_list(arr: list, t) -> bool:
    """
    Tests if list contains only object of specified types
    """
    for a in arr:
        if not isinstance(a, t):
            return False

    return True
