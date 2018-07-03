def length(address_type):
    if address_type <= 0xFF:
        return 1
    if address_type <= 0xFFFF:
        return 2
    if address_type <= 0xFFFFFF:
        return 3
    # else
    return 4


def addrtype_bytes(address_type: int):
    if address_type <= 0xFF:
        return bytes([address_type])
    if address_type <= 0xFFFF:
        return bytes([(address_type >> 8), (address_type & 0xFF)])
    if address_type <= 0xFFFFFF:
        return bytes([(address_type >> 16), (address_type >> 8), (address_type & 0xFF)])
    # else
    return bytes(
        [
            (address_type >> 24),
            (address_type >> 16),
            (address_type >> 8),
            (address_type & 0xFF),
        ]
    )


def check(address_type, raw_address):
    if address_type <= 0xFF:
        return address_type == raw_address[0]
    if address_type <= 0xFFFF:
        return address_type == (raw_address[0] << 8) | raw_address[1]
    if address_type <= 0xFFFFFF:
        return (
            address_type
            == (raw_address[0] << 16) | (raw_address[1] << 8) | raw_address[2]
        )
    # else
    return (
        address_type
        == (raw_address[0] << 24)
        | (raw_address[1] << 16)
        | (raw_address[2] << 8)
        | raw_address[3]
    )


def strip(address_type, raw_address):
    if not check(address_type, raw_address):
        raise ValueError("Invalid address")
    l = length(address_type)
    return raw_address[l:]


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
