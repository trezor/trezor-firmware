from apps.common import seed
from apps.common.confirm import confirm
from apps.common.display_address import split_address
from apps.stellar import helpers
from trezor import ui
from trezor.messages.StellarPublicKey import StellarPublicKey
from trezor.messages.StellarGetPublicKey import StellarGetPublicKey
from trezor.messages import ButtonRequestType
from trezor.ui.text import Text
from ubinascii import hexlify


async def get_public_key(ctx, msg: StellarGetPublicKey):
    node = await seed.derive_node(ctx, msg.address_n, helpers.STELLAR_CURVE)
    pubkey = seed.remove_ed25519_public_key_prefix(node.public_key())  # todo better?

    if msg.show_display:
        while True:
            if await _show(ctx, pubkey):
                break

    return StellarPublicKey(public_key=pubkey)


async def _show(ctx, pubkey: bytes):
    lines = split_address(hexlify(pubkey))
    content = Text('Export Stellar ID', ui.ICON_RECEIVE,
                   ui.NORMAL, 'Share public account ID?',  # todo only two lines are displayed
                   ui.MONO, *lines,
                   icon_color=ui.GREEN)

    return await confirm(
        ctx,
        content,
        code=ButtonRequestType.Address,
        cancel_style=ui.BTN_KEY)
