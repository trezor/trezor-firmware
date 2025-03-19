from trezor.crypto.der import encode_seq
from trezor.enums import InputScriptType


def encode_der_signature(recoverable_signature: bytes) -> bytes:
    assert len(recoverable_signature) == 65
    return encode_seq((recoverable_signature[1:33], recoverable_signature[33:65]))


def encode_raw_signature(recoverable_signature: bytes) -> bytes:
    assert len(recoverable_signature) == 65
    return recoverable_signature[1:65]


def encode_bip137_signature(
    recoverable_signature: bytes, script_type: InputScriptType
) -> bytes:
    def get_script_type_number(script_type: InputScriptType) -> int:
        if script_type == InputScriptType.SPENDADDRESS_UNCOMPRESSED:
            return 0
        if script_type == InputScriptType.SPENDADDRESS:
            return 4
        elif script_type == InputScriptType.SPENDP2SHWITNESS:
            return 8
        elif script_type == InputScriptType.SPENDWITNESS:
            return 12
        else:
            raise ValueError("Unsupported script type")

    assert len(recoverable_signature) == 65
    header = get_script_type_number(script_type) + recoverable_signature[0]
    return bytes([header]) + recoverable_signature[1:]


def decode_bip137_signature(signature: bytes) -> tuple[InputScriptType, bytes]:
    def get_script_type(header: int) -> InputScriptType:
        if 27 <= header <= 30:
            return InputScriptType.SPENDADDRESS_UNCOMPRESSED
        elif 31 <= header <= 34:
            return InputScriptType.SPENDADDRESS
        elif 35 <= header <= 38:
            return InputScriptType.SPENDP2SHWITNESS
        elif 39 <= header <= 42:
            return InputScriptType.SPENDWITNESS
        else:
            raise ValueError("Unsupported script type")

    assert len(signature) == 65
    header = signature[0]
    return get_script_type(header), bytes([header]) + signature[1:]
