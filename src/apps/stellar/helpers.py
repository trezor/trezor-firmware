from trezor.crypto import base32
import ustruct


class UiConfirmInit:

    def __init__(self, pubkey: bytes, network: str):
        self.pubkey = pubkey
        self.network = network


class UiConfirmMemo:

    def __init__(self, memo_type: int, memo_text: str):
        self.memo_type = memo_type
        self.memo_text = memo_text


class UiConfirmFinal:

    def __init__(self, fee: int, num_operations: int):
        self.fee = fee
        self.num_operations = num_operations


def confirm_init(pubkey: bytes, network: str):
    return (yield UiConfirmInit(pubkey, network))


def confirm_memo(memo_type: int, memo_text: str):
    return (yield UiConfirmMemo(memo_type, memo_text))


def confirm_final(fee: int, num_operations: int):
    return (yield UiConfirmFinal(fee, num_operations))


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
