from trezor import log, ui, wire
from trezor.crypto import bip32
from trezor.messages.CardanoAddress import CardanoAddress

from .address import _break_address_n_to_lines, derive_address_and_node
from .ui import show_swipable_with_confirmation

from apps.common import storage


async def cardano_get_address(ctx, msg):
    mnemonic = storage.get_mnemonic()
    root_node = bip32.from_mnemonic_cardano(mnemonic)

    try:
        address, _ = derive_address_and_node(root_node, msg.address_n)
    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Deriving address failed")
    mnemonic = None
    root_node = None

    if msg.show_display:
        if not await show_swipable_with_confirmation(
            ctx, address, "Export address", icon=ui.ICON_SEND, icon_color=ui.GREEN
        ):
            raise wire.ActionCancelled("Exporting cancelled")
        else:
            lines = _break_address_n_to_lines(msg.address_n)
            if not await show_swipable_with_confirmation(
                ctx, lines, "For BIP32 path", icon=ui.ICON_SEND, icon_color=ui.GREEN
            ):
                raise wire.ActionCancelled("Exporting cancelled")

    return CardanoAddress(address=address)
