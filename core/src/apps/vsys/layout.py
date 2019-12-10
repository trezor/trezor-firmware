from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.ui.scroll import Paginated
from trezor.ui.text import Text
from trezor.utils import chunks, format_amount

from apps.common.confirm import require_confirm
from apps.vsys.helpers import VSYS_AMOUNT_DIVISIBILITY


async def require_confirm_payment_tx(ctx, to, value):
    text = Text("Confirm sending payment", ui.ICON_SEND, ui.GREEN)
    text.bold(format_vsys_amount(value))
    text.normal("to")
    text.mono(*split_address(to))
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_lease_tx(ctx, to, value):
    text = Text("Confirm sending lease", ui.ICON_SEND, ui.GREEN)
    text.bold(format_vsys_amount(value))
    text.normal("to")
    text.mono(*split_address(to))
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_cancel_lease_tx(ctx, txId):
    text = Text("Confirm lease cancellation", ui.ICON_SEND, ui.GREEN)
    text.bold(txId)
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


def split_address(address):
    return chunks(address, 18)


def format_vsys_amount(value):
    formatted_value = format_amount(value, VSYS_AMOUNT_DIVISIBILITY)
    return formatted_value + " VSYS"

