from typing import TYPE_CHECKING

from trezor import utils

if TYPE_CHECKING:
    from apps.common.keychain import Keychain

_ADDRESS_MAC_KEY_PATH = [b"SLIP-0024", b"Address MAC key"]


def check_address_mac(
    address: str, mac: bytes, slip44: int, keychain: Keychain
) -> None:
    from trezor import wire
    from trezor.crypto import hashlib

    expected_mac = get_address_mac(address, slip44, keychain)
    if len(mac) != hashlib.sha256.digest_size or not utils.consteq(expected_mac, mac):
        raise wire.DataError("Invalid address MAC.")


def get_address_mac(address: str, slip44: int, keychain: Keychain) -> bytes:
    from trezor.crypto import hmac

    from .writers import write_bytes_unchecked, write_compact_size, write_uint32_le

    # k = Key(m/"SLIP-0024"/"Address MAC key")
    node = keychain.derive_slip21(_ADDRESS_MAC_KEY_PATH)

    # mac = HMAC-SHA256(key = k, msg = slip44 || address)
    mac = utils.HashWriter(hmac(hmac.SHA256, node.key()))
    address_bytes = address.encode()
    write_uint32_le(mac, slip44)
    write_compact_size(mac, len(address_bytes))
    write_bytes_unchecked(mac, address_bytes)
    return mac.get_digest()
