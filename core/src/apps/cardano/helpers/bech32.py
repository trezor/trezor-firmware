from trezor.crypto import bech32


def encode(hrp: str, data: bytes) -> str:
    converted_bits = bech32.convertbits(data, 8, 5)
    return bech32.bech32_encode(hrp, converted_bits)


def decode(hrp: str, bech: str) -> bytes:
    decoded_hrp, data = bech32.bech32_decode(bech, 130)
    if decoded_hrp != hrp:
        raise ValueError("Bech 32 decode failed")

    decoded = bech32.convertbits(data, 5, 8, False)
    if decoded is None:
        raise ValueError("Bech 32 decode failed")

    return bytes(decoded)
