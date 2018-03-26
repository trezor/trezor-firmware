
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


def nem_transaction_write_common(tx_type: int, version: int, timestamp: int, signer: bytes, fee: int, deadline: int)\
        -> bytearray:
    ret = bytearray()
    write_uint32(ret, tx_type)
    write_uint32(ret, version)
    write_uint32(ret, timestamp)

    write_bytes_with_length(ret, bytearray(signer))
    write_uint64(ret, fee)
    write_uint32(ret, deadline)

    return ret


def nem_get_version(network, mosaics=None) -> int:
    if mosaics:
        return network << 24 | 2
    return network << 24 | 1
