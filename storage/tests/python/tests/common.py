def all_ff_bytes(data: bytes):
    return all(i == 0xFF for i in data)
