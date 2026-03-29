from micropython import const
from trezorcrypto import bip32

from storage import device

# The HARDENED flag is taken from apps.common.paths
# It is not imported to save on resources
HARDENED = const(0x8000_0000)


def derive_static_key_pair() -> tuple[bytes, bytes]:
    node_int = HARDENED | int.from_bytes(b"\x00THP", "big")
    node = bip32.from_seed(device.get_device_secret(), "curve25519")
    node.derive(node_int)

    trezor_static_private_key = node.private_key()
    trezor_static_public_key = node.public_key()[1:33]
    # Note: the first byte (\x01) of the public key is removed, as it
    # only indicates the type of the elliptic curve used

    return trezor_static_private_key, trezor_static_public_key


def get_trezor_static_public_key() -> bytes:
    _, public_key = derive_static_key_pair()
    return public_key
