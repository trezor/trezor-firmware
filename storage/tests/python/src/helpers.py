import sys

from . import consts


def expand_to_log_size(value: int) -> int:
    result = 0
    for i in range(0, consts.PIN_LOG_SIZE, 4):
        result = result | (value << i * 8)
    return result


def to_int_by_words(array: bytes) -> int:
    """
    Converts array of bytes into an int by reading word size
    of bytes then converted to int using the system's endianness.
    """
    assert len(array) % consts.WORD_SIZE == 0
    n = 0
    for i in range(0, len(array), consts.WORD_SIZE):
        n = (n << (consts.WORD_SIZE * 8)) + int.from_bytes(
            array[i : i + consts.WORD_SIZE], sys.byteorder
        )
    return n


def to_bytes_by_words(n: int, length: int) -> bytes:
    """
    Converting int back to bytes by words.
    """
    mask = (1 << (consts.WORD_SIZE * 8)) - 1
    array = bytes()
    for i in reversed(range(0, length, consts.WORD_SIZE)):
        array = array + ((n >> (i * 8)) & mask).to_bytes(
            consts.WORD_SIZE, sys.byteorder
        )
    return array


def int_to_word(n: int) -> bytes:
    return n.to_bytes(consts.WORD_SIZE, sys.byteorder)


def word_to_int(b: bytes) -> int:
    return int.from_bytes(b, sys.byteorder)
