from apps.common.writers import (
    write_bytes,
    write_uint8,
    write_uint32_be,
    write_uint64_be,
)

write_uint8 = write_uint8
write_uint32 = write_uint32_be
write_uint64 = write_uint64_be
write_bytes = write_bytes


def write_bool(w: bytearray, boolean: bool):
    if boolean:
        write_uint8(w, 255)
    else:
        write_uint8(w, 0)


# write uint16 in be
def write_uint16(w: bytearray, n: int):
    w.append((n >> 8) & 0xFF)
    w.append(n & 0xFF)
