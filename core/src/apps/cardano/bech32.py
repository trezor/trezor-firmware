from trezor.crypto import bech32


def bech32_encode(human_readable_part: str, data: bytes) -> str:
    converted_bits = bech32.convertbits(data, 8, 5)
    return bech32.bech32_encode(human_readable_part, converted_bits)


def bech32_decode(human_readable_part: str, bech: str) -> bytes:
    decoded_human_readable_part, data = bech32.bech32_decode(bech)
    if decoded_human_readable_part != human_readable_part:
        return None
    decoded = bech32.convertbits(data, 5, 8, False)
    return bytes(decoded)
