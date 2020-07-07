from trezor.crypto import bech32


"""
Helper function to encode data longer than segwit addresses. We don't
need the decode function. If it ever is needed trezor.crypto.bech32
implementation needs to be updated for decoding longer strings than
90 characters.
"""


def bech32_encode(human_readable_part: str, data: bytes) -> str:
    converted_bits = bech32.convertbits(data, 8, 5)
    return bech32.bech32_encode(human_readable_part, converted_bits)
