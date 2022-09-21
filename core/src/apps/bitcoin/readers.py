from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.utils import BufferReader


def read_memoryview_prefixed(r: BufferReader) -> memoryview:
    from apps.common.readers import read_compact_size

    n = read_compact_size(r)
    return r.read_memoryview(n)


def read_op_push(r: BufferReader) -> int:
    get = r.get  # local_cache_attribute

    prefix = get()
    if prefix < 0x4C:
        n = prefix
    elif prefix == 0x4C:
        n = get()
    elif prefix == 0x4D:
        n = get()
        n += get() << 8
    elif prefix == 0x4E:
        n = get()
        n += get() << 8
        n += get() << 16
        n += get() << 24
    else:
        raise ValueError
    return n
