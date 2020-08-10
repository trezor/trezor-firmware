from micropython import const

if False:
    from typing import List


def variable_length_encode(number: int) -> bytes:
    """
    Used for pointer encoding in pointer address.
    Encoding description can be found here:
    https://en.wikipedia.org/wiki/Variable-length_quantity
    """
    if number < 0:
        raise ValueError("Negative numbers not supported. Number supplied: %s" % number)

    encoded = []

    bit_length = len(bin(number)[2:])
    encoded.append(number & 127)

    while bit_length > 7:
        number >>= 7
        bit_length -= 7
        encoded.insert(0, (number & 127) + 128)

    return bytes(encoded)


def to_account_path(path: List[int]) -> List[int]:
    ACCOUNT_PATH_LENGTH = const(3)
    return path[:ACCOUNT_PATH_LENGTH]
