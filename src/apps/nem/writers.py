
def write_uint32(w, n: int):
    w.append(n & 0xFF)
    w.append((n >> 8) & 0xFF)
    w.append((n >> 16) & 0xFF)
    w.append((n >> 24) & 0xFF)


def write_uint64(w, n: int):
    w.append(n & 0xFF)
    w.append((n >> 8) & 0xFF)
    w.append((n >> 16) & 0xFF)
    w.append((n >> 24) & 0xFF)
    w.append((n >> 32) & 0xFF)
    w.append((n >> 40) & 0xFF)
    w.append((n >> 48) & 0xFF)
    w.append((n >> 56) & 0xFF)


def write_bytes(w, buf: bytearray):
    w.extend(buf)


def write_bytes_with_length(w, buf: bytearray):
    write_uint32(w, len(buf))
    write_bytes(w, buf)
