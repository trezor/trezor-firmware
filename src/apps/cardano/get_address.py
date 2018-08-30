from trezor import log, ui, wire
from trezor.crypto import bip32
from trezor.messages.CardanoAddress import CardanoAddress

from .address import derive_address_and_node, validate_full_path
from .layout import confirm_with_pagination

from apps.common import paths, seed, storage


async def get_address(ctx, msg):
    await paths.validate_path(ctx, validate_full_path, path=msg.address_n)

    mnemonic = storage.get_mnemonic()
    passphrase = await seed._get_cached_passphrase(ctx)
    root_node = bip32.from_mnemonic_cardano(mnemonic, passphrase)

    try:
        address, _ = derive_address_and_node(root_node, msg.address_n)
    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Deriving address failed")
    mnemonic = None
    root_node = None

    if msg.show_display:
        if not await confirm_with_pagination(
            ctx, address, "Export address", icon=ui.ICON_SEND, icon_color=ui.GREEN
        ):
            raise wire.ActionCancelled("Exporting cancelled")

    return CardanoAddress(address=address)
