from trezor import log, ui, wire
from trezor.messages.CardanoAddress import CardanoAddress

from apps.cardano import seed
from apps.cardano.address import derive_address_and_node, validate_full_path
from apps.cardano.layout import confirm_with_pagination
from apps.common import paths


async def get_address(ctx, msg):
    keychain = await seed.get_keychain(ctx)

    await paths.validate_path(ctx, validate_full_path, path=msg.address_n)

    try:
        address, _ = derive_address_and_node(keychain, msg.address_n)
    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Deriving address failed")

    if msg.show_display:
        if not await confirm_with_pagination(
            ctx, address, "Export address", icon=ui.ICON_SEND, icon_color=ui.GREEN
        ):
            raise wire.ActionCancelled("Exporting cancelled")

    return CardanoAddress(address=address)
