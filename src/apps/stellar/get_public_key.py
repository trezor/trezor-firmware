from ubinascii import hexlify

from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.messages.StellarGetPublicKey import StellarGetPublicKey
from trezor.messages.StellarPublicKey import StellarPublicKey
from trezor.ui.text import Text

from apps.common import seed
from apps.common.confirm import confirm
from apps.common.display_address import split_address
from apps.stellar import helpers


async def get_public_key(ctx, msg: StellarGetPublicKey):
    node = await seed.derive_node(ctx, msg.address_n, helpers.STELLAR_CURVE)
    pubkey = seed.remove_ed25519_prefix(node.public_key())

    if msg.show_display:
        while True:
            if await _show(ctx, pubkey):
                break

    return StellarPublicKey(public_key=pubkey)


async def _show(ctx, pubkey: bytes):
    lines = split_address(hexlify(pubkey))
    text = Text("Export Stellar ID", ui.ICON_RECEIVE, icon_color=ui.GREEN)
    text.mono(*lines)

    return await confirm(
        ctx, text, code=ButtonRequestType.Address, cancel_style=ui.BTN_KEY
    )
