from trezor.messages.NEMTransactionCommon import NEMTransactionCommon


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


def write_common(common: NEMTransactionCommon,
                 public_key: bytearray,
                 transaction_type: int,
                 version: int = None) -> bytearray:
    ret = bytearray()

    write_uint32(ret, transaction_type)
    if version is None:
        version = common.network << 24 | 1
    write_uint32(ret, version)
    write_uint32(ret, common.timestamp)

    write_bytes_with_length(ret, public_key)
    write_uint64(ret, common.fee)
    write_uint32(ret, common.deadline)

    return ret
