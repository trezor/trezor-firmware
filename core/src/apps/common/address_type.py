def length(address_type: int) -> int:
    if address_type <= 0xFF:
        return 1
    if address_type <= 0xFFFF:
        return 2
    if address_type <= 0xFF_FFFF:
        return 3
    # else
    return 4


def tobytes(address_type: int) -> bytes:
    return address_type.to_bytes(length(address_type), "big")


def check(address_type: int, raw_address: bytes) -> bool:
    return raw_address.startswith(tobytes(address_type))


def strip(address_type: int, raw_address: bytes) -> bytes:
    if not check(address_type, raw_address):
        raise ValueError
    return raw_address[length(address_type) :]
