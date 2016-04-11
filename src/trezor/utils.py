def hexlify(data: bytes) -> str:
    return ''.join(['%02x' % b for b in data])

def unhexlify(data: str) -> bytes:
    return bytes([int(data[i:i+2], 16) for i in range(0, len(data), 2)])
