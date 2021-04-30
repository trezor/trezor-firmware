from trezor.messages import RippleAddress, RippleGetAddress
from trezor.ui.layouts import show_address

from apps.common import paths
from apps.common.keychain import auto_keychain
from apps.common.layout import address_n_to_str

from .helpers import address_from_public_key


@auto_keychain(__name__)
async def get_address(ctx, msg: RippleGetAddress, keychain):
    await paths.validate_path(ctx, keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    pubkey = node.public_key()
    address = address_from_public_key(pubkey)

    if msg.show_display:
        desc = address_n_to_str(msg.address_n)
        await show_address(ctx, address=address, address_qr=address, desc=desc)

    return RippleAddress(address=address)
