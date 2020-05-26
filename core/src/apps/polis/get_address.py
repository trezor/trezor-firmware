from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha3_256
from trezor.messages.PolisAddress import PolisAddress

from apps.common import paths
from apps.common.layout import address_n_to_str, show_address, show_qr
from apps.polis import CURVE, networks
from apps.polis.address import address_from_bytes, validate_full_path
from apps.polis.keychain import with_keychain_from_path


@with_keychain_from_path
async def get_address(ctx, msg, keychain):
    await paths.validate_path(ctx, validate_full_path, keychain, msg.address_n, CURVE)
    return PolisAddress(address="address")
