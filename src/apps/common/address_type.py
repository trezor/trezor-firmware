def length(address_type):
    if address_type <= 0xFF:
        return 1
    if address_type <= 0xFFFF:
        return 2
    if address_type <= 0xFFFFFF:
        return 3
    # else
    return 4


def tobytes(address_type: int):
    return address_type.to_bytes(length(address_type), "big")


def check(address_type, raw_address):
    return raw_address.startswith(tobytes(address_type))


def strip(address_type, raw_address):
    if not check(address_type, raw_address):
        raise ValueError("Invalid address")
    return raw_address[length(address_type) :]


def split(coin, raw_address):
    for f in (
        "address_type",
        "address_type_p2sh",
        "address_type_p2wpkh",
        "address_type_p2wsh",
    ):
        at = getattr(coin, f)
        if at is not None and check(at, raw_address):
            l = length(at)
            return raw_address[:l], raw_address[l:]
    raise ValueError("Invalid address")
