from apps.common import seed
from apps.common.confirm import confirm
from trezor import ui
from trezor.messages.StellarPublicKey import StellarPublicKey
from trezor.messages.StellarGetPublicKey import StellarGetPublicKey
from trezor.messages import ButtonRequestType
from trezor.ui.text import Text
from trezor.utils import chunks
from trezor.crypto import base32
import ustruct

STELLAR_CURVE = 'ed25519'


async def get_public_key(ctx, msg: StellarGetPublicKey):
    node = await seed.derive_node(ctx, msg.address_n, STELLAR_CURVE)
    pubkey = seed.remove_ed25519_public_key_prefix(node.public_key())  # todo better?

    while True:
        if await _show(ctx, _address_from_public_key(pubkey)):
            break

    return StellarPublicKey(public_key=pubkey)


async def _show(ctx, address: str):
    lines = _split_address(address)
    content = Text('Export Stellar ID', ui.ICON_RECEIVE,
                   ui.NORMAL, 'Share public account ID?',
                   ui.MONO, *lines,
                   icon_color=ui.GREEN)

    return await confirm(
        ctx,
        content,
        code=ButtonRequestType.Address,
        cancel_style=ui.BTN_KEY)


def _split_address(address: str):
    return chunks(address, 17)


def _address_from_public_key(pubkey: bytes):
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
