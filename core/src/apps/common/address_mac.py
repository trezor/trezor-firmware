from typing import TYPE_CHECKING

from trezor import utils

if TYPE_CHECKING:
    from buffer_types import AnyBytes

    from apps.common.keychain import Keychain
    from apps.common.paths import Bip32Path

_ADDRESS_MAC_KEY_PATH = [b"SLIP-0024", b"Address MAC key"]


def check_address_mac(
    address: str, mac: AnyBytes, slip44: int, address_n: Bip32Path, keychain: Keychain
) -> None:
    from trezor import wire
    from trezor.crypto import hashlib

    expected_mac = get_address_mac(address, slip44, address_n, keychain)
    if len(mac) != hashlib.sha256.digest_size or not utils.consteq(expected_mac, mac):
        raise wire.DataError("Invalid address MAC.")


def get_address_mac(
    address: str, slip44: int, address_n: Bip32Path, keychain: Keychain
) -> bytes:
    from trezor.crypto import hmac

    from .writers import write_bytes_unchecked, write_compact_size, write_uint32_le

    # k = Key(m/"SLIP-0024"/"Address MAC key")
    node = keychain.derive_slip21(_ADDRESS_MAC_KEY_PATH)

    # mac = HMAC-SHA256(key = k, msg = slip44 || address)
    mac = utils.HashWriter(hmac(hmac.SHA256, node.key()))
    address_bytes = address.encode()
    write_uint32_le(mac, slip44)
    write_compact_size(mac, len(address_n))
    for n in address_n:
        write_uint32_le(mac, n)
    write_compact_size(mac, len(address_bytes))
    write_bytes_unchecked(mac, address_bytes)
    return mac.get_digest()


def get_policy_mac(
    policy_name: str,
    script: str,
    xpubs: list[str],
    blocks: int,
    slip44: int,
    keychain: Keychain,
) -> bytes:
    from trezor.crypto import hmac

    from .writers import (
        write_bytes_unchecked,
        write_compact_size,
        write_uint32_le,
        write_uint64_le,
    )

    node = keychain.derive_slip21([b"SLIP-0019", b"Trezor-Policy"])

    mac = utils.HashWriter(hmac(hmac.SHA256, node.key()))

    write_uint32_le(mac, slip44)
    policy_name_bytes = policy_name.encode()
    write_compact_size(mac, len(policy_name_bytes))
    write_bytes_unchecked(mac, policy_name_bytes)
    script_bytes = script.encode()
    write_compact_size(mac, len(script_bytes))
    write_bytes_unchecked(mac, script_bytes)
    for xpub in xpubs:
        xpub_bytes = xpub.encode()
        write_compact_size(mac, len(xpub_bytes))
        write_bytes_unchecked(mac, xpub_bytes)
    write_uint64_le(mac, blocks)

    return mac.get_digest()
