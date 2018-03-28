from apps.common.confirm import *
from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.messages.NEMMosaicDefinition import NEMMosaicDefinition
from trezor.ui.text import Text
from trezor.ui.scroll import Scrollpage, animate_swipe, paginate
from trezor.utils import chunks, format_amount, split_words
from .helpers import *


async def require_confirm_tx(ctx, recipient, value):
    content = Text('Confirm sending', ui.ICON_SEND,
                   ui.BOLD, format_amount(value, NEM_MAX_DIVISIBILITY) + ' NEM',
                   ui.NORMAL, 'to',
                   ui.MONO, *split_address(recipient),
                   icon_color=ui.GREEN)
    await require_hold_to_confirm(ctx, content, ButtonRequestType.SignTx)  # we use SignTx, not ConfirmOutput, for compatibility with T1


async def require_confirm_action(ctx, action: str):
    content = Text('Confirm sending', ui.ICON_SEND,
                   ui.NORMAL, *split_words(action, 18),
                   icon_color=ui.GREEN)
    await require_confirm(ctx, content, ButtonRequestType.ConfirmOutput)


@ui.layout
async def _show_page(page: int, page_count: int, content):
    content = Scrollpage(content[page], page, page_count)
    if page + 1 == page_count:
        await ConfirmDialog(content)
    else:
        content.render()
        await animate_swipe()


async def require_confirm_properties(ctx, definition: NEMMosaicDefinition):
    properties = _get_mosaic_properties(definition)
    first_page = const(0)
    paginator = paginate(_show_page, len(properties), first_page, properties)
    await ctx.wait(paginator)


def _get_mosaic_properties(definition: NEMMosaicDefinition):
    properties = []
    if definition.description:
        t = Text('Confirm properties', ui.ICON_SEND,
                 ui.BOLD, 'Description:',
                 ui.NORMAL, definition.description)
        properties.append(t)
    if definition.transferable:
        transferable = 'Yes'
    else:
        transferable = 'No'
    t = Text('Confirm properties', ui.ICON_SEND,
             ui.BOLD, 'Transferable?',
             ui.NORMAL, transferable)
    properties.append(t)
    if definition.mutable_supply:
        imm = 'mutable'
    else:
        imm = 'immutable'
    if definition.supply:
        t = Text('Confirm properties', ui.ICON_SEND,
                 ui.BOLD, 'Initial supply:',
                 ui.NORMAL, format_amount(definition.supply, definition.divisibility),
                 ui.NORMAL, imm)
        properties.append(t)
    return properties


async def require_confirm_final(ctx, action: str, fee: int):
    content = Text('Confirm sending', ui.ICON_SEND,
                   ui.NORMAL, 'Create ', action,
                   ui.BOLD, 'paying ' + format_amount(fee, NEM_MAX_DIVISIBILITY) + ' XEM',
                   ui.NORMAL, 'for transaction fee?',
                   icon_color=ui.GREEN)
    await require_hold_to_confirm(ctx, content, ButtonRequestType.SignTx)  # we use SignTx, not ConfirmOutput, for compatibility with T1


async def require_confirm_payload(ctx, payload: bytes, encrypt=False):
    payload = str(payload, 'utf-8')
    if encrypt:
        content = Text('Send encrypted?', ui.ICON_SEND,
                       ui.NORMAL, *split_words(payload, 18))
    else:
        content = Text('Send unencrypted?', ui.ICON_SEND,
                       ui.NORMAL, *split_words(payload, 18),
                       icon_color=ui.RED)
    await require_confirm(ctx, content, ButtonRequestType.ConfirmOutput)


def split_address(data):
    return chunks(data, 17)
