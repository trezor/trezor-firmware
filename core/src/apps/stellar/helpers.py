from trezor.crypto import base32


def public_key_from_address(address: str) -> bytes:
    """Extracts public key from an address
    Stellar address is in format:
    <1-byte version> <32-bytes ed25519 public key> <2-bytes CRC-16 checksum>
    """
    from trezor.wire import ProcessError

    b = base32.decode(address)
    # verify checksum - function deleted as it saved 50 bytes from the binary
    if _crc16_checksum(b[:-2]) != b[-2:]:
        raise ProcessError("Invalid address checksum")
    return b[1:-2]


def address_from_public_key(pubkey: bytes) -> str:
    """Returns the base32-encoded version of public key bytes (G...)"""
    address = bytearray()
    address.append(6 << 3)  # version -> 'G'
    address.extend(pubkey)
    address.extend(_crc16_checksum(bytes(address)))  # checksum

    return base32.encode(address)


def encode_contract(raw_key: bytes) -> str:
    """Returns the base32-encoded version of contract address bytes (C...)"""
    address = bytearray()
    address.append(2 << 3)  # version -> 'C'
    address.extend(raw_key)
    address.extend(_crc16_checksum(bytes(address)))  # checksum

    return base32.encode(address)


def decode_contract(contract: str) -> bytes:
    """Extracts raw key from a contract address
    Contract address is in format:
    <1-byte version> <32-bytes contract key> <2-bytes CRC-16 checksum>
    """
    from trezor.wire import ProcessError

    b = base32.decode(contract)
    # verify checksum - function deleted as it saved 50 bytes from the binary
    if _crc16_checksum(b[:-2]) != b[-2:]:
        raise ProcessError("Invalid address checksum")
    return b[1:-2]


def _crc16_checksum(data: bytes) -> bytes:
    """Returns the CRC-16 checksum of bytearray bytes

    Ported from Java implementation at: http://introcs.cs.princeton.edu/java/61data/CRC16CCITT.java.html

    Initial value changed to 0x0000 to match Stellar configuration.
    """
    import ustruct

    crc = 0x0000
    polynomial = 0x1021

    for byte in data:
        for i in range(8):
            bit = (byte >> (7 - i) & 1) == 1
            c15 = (crc >> 15 & 1) == 1
            crc <<= 1
            if c15 ^ bit:
                crc ^= polynomial

    return ustruct.pack("<H", crc & 0xFFFF)


def bytes_to_int(data: bytes, signed: bool = False) -> int:
    """Converts bytes to int (big endian)"""
    num = 0
    for byte in data:
        num = (num << 8) + byte
    if signed and (data[0] & 0x80):
        num -= 1 << (8 * len(data))
    return num
