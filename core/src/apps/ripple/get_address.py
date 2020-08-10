from trezor.messages.RippleAddress import RippleAddress
from trezor.messages.RippleGetAddress import RippleGetAddress

from apps.common import paths
from apps.common.keychain import with_slip44_keychain
from apps.common.layout import address_n_to_str, show_address, show_qr
from apps.ripple import CURVE, SLIP44_ID, helpers


@with_slip44_keychain(SLIP44_ID, CURVE, allow_testnet=True)
async def get_address(ctx, msg: RippleGetAddress, keychain):
    await paths.validate_path(
        ctx, helpers.validate_full_path, keychain, msg.address_n, CURVE
    )

    node = keychain.derive(msg.address_n)
    pubkey = node.public_key()
    address = helpers.address_from_public_key(pubkey)

    if msg.show_display:
        desc = address_n_to_str(msg.address_n)
        while True:
            if await show_address(ctx, address, desc=desc):
                break
            if await show_qr(ctx, address, desc=desc):
                break

    return RippleAddress(address=address)
