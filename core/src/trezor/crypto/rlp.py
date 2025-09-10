from micropython import const
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from buffer_types import AnyBytes

    from trezor.utils import Writer

    # The intention below is basically:
    # RLPItem = int | bytes | list[RLPItem]
    # That will not typecheck though. Type `list` is invariant in its parameter, meaning
    # that we cannot pass list[bytes] into a list[RLPItem] parameter (what if the
    # function wanted to append an int?). We do want to enforce that it's a `list`, not
    # a generic `Sequence` (because we do isinstance checks for a list). We are however
    # only reading from the list and passing into things that consume a RLPItem. Hence
    # we have to enumerate single-type lists as well as the universal list[RLPItem].
    RLPList = list[int] | list[AnyBytes] | list["RLPItem"]
    RLPItem = RLPList | AnyBytes | int


STRING_HEADER_BYTE = const(0x80)
LIST_HEADER_BYTE = const(0xC0)


def _byte_size(x: int) -> int:
    if x < 0:
        raise ValueError  # only unsigned ints are supported
    for exp in range(64):
        if x < 0x100**exp:
            return exp

    raise ValueError  # int is too large


def int_to_bytes(x: int) -> bytes:
    return x.to_bytes(_byte_size(x), "big")


def write_header(
    w: Writer,
    length: int,
    header_byte: int,
    data_start: AnyBytes | None = None,
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


def header_length(length: int, data_start: AnyBytes | None = None) -> int:
    if length == 1 and data_start is not None and data_start[0] <= 0x7F:
        # no header when encoding one byte below 0x80
        return 0

    if length <= 55:
        return 1

    return 1 + _byte_size(length)


def length(item: RLPItem) -> int:
    data: AnyBytes | None = None
    if isinstance(item, int):
        data = int_to_bytes(item)
        item_length = len(data)
    elif isinstance(item, (bytes, bytearray, memoryview)):
        data = item
        item_length = len(item)
    elif isinstance(item, list):
        item_length = sum(length(i) for i in item)
    else:
        raise TypeError

    return header_length(item_length, data) + item_length


def _write_string(w: Writer, string: AnyBytes) -> None:
    write_header(w, len(string), STRING_HEADER_BYTE, string)
    w.extend(string)


def _write_list(w: Writer, lst: RLPList) -> None:
    payload_length = sum(length(item) for item in lst)
    write_header(w, payload_length, LIST_HEADER_BYTE)
    for item in lst:
        write(w, item)


def write(w: Writer, item: RLPItem) -> None:
    if isinstance(item, int):
        _write_string(w, int_to_bytes(item))
    elif isinstance(item, (bytes, bytearray, memoryview)):
        _write_string(w, item)
    elif isinstance(item, list):
        _write_list(w, item)
    else:
        raise TypeError
