from trezor import ui
from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.components.tt.text import Text

from apps.common.confirm import require_confirm, require_hold_to_confirm
from apps.common.layout import split_address

from . import helpers


async def require_confirm_fee(ctx, fee):
    text = Text("Confirm fee", ui.ICON_SEND, ui.GREEN)
    text.normal("Transaction fee:")
    text.bold(format_amount(fee, helpers.DECIMALS) + " XRP")
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def require_confirm_destination_tag(ctx, tag):
    text = Text("Confirm tag", ui.ICON_SEND, ui.GREEN)
    text.normal("Destination tag:")
    text.bold(str(tag))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def require_confirm_tx(ctx, to, value):
    text = Text("Confirm sending", ui.ICON_SEND, ui.GREEN)
    text.bold(format_amount(value, helpers.DECIMALS) + " XRP")
    text.normal("to")
    text.mono(*split_address(to))
    await require_hold_to_confirm(ctx, text, ButtonRequestType.SignTx)
