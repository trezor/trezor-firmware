from micropython import const

from trezor import ui
from trezor.strings import format_amount
from trezor.ui.scroll import Paginated
from trezor.ui.text import Text
from trezor.utils import chunks

from apps.common.confirm import require_confirm, require_hold_to_confirm

from .. import protocol_magics


def format_coin_amount(amount):
    return "%s %s" % (format_amount(amount, 6), "ADA")


async def confirm_sending(ctx, amount, to):
    to_lines = list(chunks(to, 17))

    t1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    t1.normal("Confirm sending:")
    t1.bold(format_coin_amount(amount))
    t1.normal("to:")
    t1.bold(to_lines[0])

    PER_PAGE = const(4)
    pages = [t1]
    if len(to_lines) > 1:
        to_pages = list(chunks(to_lines[1:], PER_PAGE))
        for page in to_pages:
            t = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
            for line in page:
                t.bold(line)
            pages.append(t)

    await require_confirm(ctx, Paginated(pages))


async def confirm_transaction(ctx, amount, fee, protocol_magic):
    t1 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    t1.normal("Total amount:")
    t1.bold(format_coin_amount(amount))
    t1.normal("including fee:")
    t1.bold(format_coin_amount(fee))

    t2 = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    t2.normal("Network:")
    t2.bold(protocol_magics.to_ui_string(protocol_magic))

    await require_hold_to_confirm(ctx, Paginated([t1, t2]))
