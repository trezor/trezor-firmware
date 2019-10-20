from trezor.messages.BinanceAddress import BinanceAddress
from trezor.messages.BinanceGetAddress import BinanceGetAddress

from apps.binance import CURVE, helpers
from apps.common import paths
from apps.common.layout import address_n_to_str, show_address, show_qr


async def get_address(ctx, msg: BinanceGetAddress, keychain):
    HRP = "bnb"

    await paths.validate_path(
        ctx, helpers.validate_full_path, keychain, msg.address_n, CURVE
    )

    node = keychain.derive(msg.address_n)
    pubkey = node.public_key()
    address = helpers.address_from_public_key(pubkey, HRP)
    if msg.show_display:
        desc = address_n_to_str(msg.address_n)
        while True:
            if await show_address(ctx, address, desc=desc):
                break
            if await show_qr(ctx, address, desc=desc):
                break

    return BinanceAddress(address=address)
