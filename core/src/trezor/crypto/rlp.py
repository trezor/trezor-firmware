from micropython import const

if False:
    from typing import Union
    from trezor.utils import Writer

    # what we want:
    # RLPItem = Union[list["RLPItem"], bytes, int]
    # what mypy can process:
    RLPItem = Union[list, bytes, int]


STRING_HEADER_BYTE = const(0x80)
LIST_HEADER_BYTE = const(0xC0)


def _byte_size(x: int) -> int:
    if x < 0:
        raise ValueError  # only unsigned ints are supported
    for exp in range(64):
        if x < 0x100 ** exp:
            return exp

    raise ValueError  # int is too large


def int_to_bytes(x: int) -> bytes:
    return x.to_bytes(_byte_size(x), "big")


def write_header(
    w: Writer,
    length: int,
    header_byte: int,
    data_start: bytes | None = None,
) -> None:
    if length == 1 and data_start is not None and data_start[0] <= 0x7F:
        # no header when encoding one byte below 0x80
        pass

    elif length <= 55:
        w.append(header_byte + length)

    else:
        encoded_length = int_to_bytes(length)
        w.append(header_byte + 55 + len(encoded_length))
        w.extend(encoded_length)


def header_length(length: int, data_start: bytes | None = None) -> int:
    if length == 1 and data_start is not None and data_start[0] <= 0x7F:
        # no header when encoding one byte below 0x80
        return 0

    if length <= 55:
        return 1

    return 1 + _byte_size(length)


def length(item: RLPItem) -> int:
    data: bytes | None = None
    if isinstance(item, int):
        data = int_to_bytes(item)
        item_length = len(data)
    elif isinstance(item, (bytes, bytearray)):
        data = item
        item_length = len(item)
    elif isinstance(item, list):
        item_length = sum(length(i) for i in item)
    else:
        raise TypeError

    return header_length(item_length, data) + item_length


def write_string(w: Writer, string: bytes) -> None:
    write_header(w, len(string), STRING_HEADER_BYTE, string)
    w.extend(string)


def write_list(w: Writer, lst: list[RLPItem]) -> None:
    payload_length = sum(length(item) for item in lst)
    write_header(w, payload_length, LIST_HEADER_BYTE)
    for item in lst:
        write(w, item)


def write(w: Writer, item: RLPItem) -> None:
    if isinstance(item, int):
        write_string(w, int_to_bytes(item))
    elif isinstance(item, (bytes, bytearray)):
        write_string(w, item)
    elif isinstance(item, list):
        write_list(w, item)
    else:
        raise TypeError
