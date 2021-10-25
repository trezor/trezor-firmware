from trezor.messages import ZcashGetAddress, ZcashAddress
from trezor.ui.layouts import show_address

from apps.common import paths, seed
from apps.common.paths import HARDENED

from trezor.crypto import zcash
from trezor.crypto import base32
from trezor.crypto import random

from trezor import log

if False:
    from trezor.wire import Context

async def get_address(
    ctx: Context,
    msg: ZcashGetAddress
) -> ZcashAddress:
    # TODO: consider seed shadowing
    secret = seed.get_seed(ctx) # TODO: this returns nothing
    secret = 32*b"A"

    # TODO: random diversifier
    
    log.warning(__name__, "get_address args: {}, {}, {}".format(secret, msg.account, msg.diversifier_index))
    address = zcash.get_address(secret, msg.account, msg.diversifier_index)

    if msg.show_display:
        title = "Zcash Orchard address"
        await show_address(
            ctx, address=address, address_qr=address, title=title
        )

    return ZcashAddress(address=address)