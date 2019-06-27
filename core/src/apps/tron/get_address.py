from trezor.crypto.curve import secp256k1
from trezor.messages.TronAddress import TronAddress

from apps.common import paths
from apps.common.layout import address_n_to_str, show_address, show_qr
from apps.tron import CURVE
from apps.tron.address import get_address_from_public_key, validate_full_path


async def get_address(ctx, msg, keychain):
    address_n = msg.address_n or ()
    await paths.validate_path(ctx, validate_full_path, keychain, address_n, CURVE)

    node = keychain.derive(address_n)
    seckey = node.private_key()
    public_key = secp256k1.publickey(seckey, False)
    address = get_address_from_public_key(public_key[:65])

    if msg.show_display:
        desc = address_n_to_str(address_n)
        while True:
            if await show_address(ctx, address, desc=desc):
                break
            if await show_qr(ctx, address, desc=desc):
                break

    return TronAddress(address=address)
