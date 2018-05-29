from apps.common import seed
from apps.common.confirm import confirm
from apps.stellar import helpers
from trezor import ui
from trezor.messages.StellarPublicKey import StellarPublicKey
from trezor.messages.StellarGetPublicKey import StellarGetPublicKey
from trezor.messages import ButtonRequestType
from trezor.ui.text import Text
from trezor.utils import chunks

STELLAR_CURVE = 'ed25519'


async def get_public_key(ctx, msg: StellarGetPublicKey):
    node = await seed.derive_node(ctx, msg.address_n, STELLAR_CURVE)
    pubkey = seed.remove_ed25519_public_key_prefix(node.public_key())  # todo better?

    while True:
        if await _show(ctx, helpers.address_from_public_key(pubkey)):
            break

    return StellarPublicKey(public_key=pubkey)


async def _show(ctx, address: str):
    lines = _split_address(address)
    content = Text('Export Stellar ID', ui.ICON_RECEIVE,
                   ui.NORMAL, 'Share public account ID?',
                   ui.MONO, *lines,
                   icon_color=ui.GREEN)

    return await confirm(
        ctx,
        content,
        code=ButtonRequestType.Address,
        cancel_style=ui.BTN_KEY)


def _split_address(address: str):
    return chunks(address, 17)
