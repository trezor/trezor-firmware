from trezor.crypto import base32
import ustruct


def address_from_public_key(pubkey: bytes):
    """Returns the base32-encoded version of public key bytes (G...)"""

    address = bytearray()
    address.append(6 << 3)  # version -> 'G'
    address.extend(pubkey)
    address.extend(ustruct.pack("<H", _crc16_checksum(address)))  # checksum

    return base32.encode(address)


def _crc16_checksum(data: bytearray):
    """Returns the CRC-16 checksum of bytearray bytes

    Ported from Java implementation at: http://introcs.cs.princeton.edu/java/61data/CRC16CCITT.java.html

    Initial value changed to 0x0000 to match Stellar configuration.
    """
    crc = 0x0000
    polynomial = 0x1021

    for byte in data:
        for i in range(8):
            bit = ((byte >> (7 - i) & 1) == 1)
            c15 = ((crc >> 15 & 1) == 1)
            crc <<= 1
            if c15 ^ bit:
                crc ^= polynomial

    return crc & 0xffff
