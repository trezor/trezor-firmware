from apps.common.confirm import *
from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.messages.NEMMosaicDefinition import NEMMosaicDefinition
from trezor.messages import NEMMosaicLevy
from trezor.ui.text import Text
from trezor.ui.scroll import Scrollpage, animate_swipe, paginate
from trezor.utils import chunks, format_amount, split_words
from .helpers import *


async def require_confirm_action(ctx, action: str):
    content = Text('Confirm action', ui.ICON_SEND,
                   ui.NORMAL, *split_words(action, 18),
                   icon_color=ui.GREEN)
    await require_confirm(ctx, content, ButtonRequestType.ConfirmOutput)


async def require_confirm_fee(ctx, action: str, fee: int):
    content = Text('Confirm fee', ui.ICON_SEND,
                   ui.NORMAL, action,
                   ui.BOLD, format_amount(fee, NEM_MAX_DIVISIBILITY) + ' XEM',
                   icon_color=ui.GREEN)
    await require_confirm(ctx, content, ButtonRequestType.ConfirmOutput)


async def require_confirm_transfer(ctx, recipient, value):
    content = Text('Confirm transfer', ui.ICON_SEND,
                   ui.BOLD, 'Send ' + format_amount(value, NEM_MAX_DIVISIBILITY) + ' XEM',
                   ui.NORMAL, 'to',
                   ui.MONO, *split_address(recipient),
                   icon_color=ui.GREEN)
    await require_confirm(ctx, content, ButtonRequestType.ConfirmOutput)


async def require_confirm_address(ctx, action: str, address: str):
    content = Text('Confirm address', ui.ICON_SEND,
                   ui.NORMAL, action,
                   ui.MONO, *split_address(address),
                   icon_color=ui.GREEN)
    await require_confirm(ctx, content, ButtonRequestType.ConfirmOutput)


async def require_confirm_final(ctx, fee: int):
    content = Text('Final confirm', ui.ICON_SEND,
                   ui.NORMAL, 'Sign this transaction',
                   ui.BOLD, 'and pay ' + format_amount(fee, NEM_MAX_DIVISIBILITY) + ' XEM',
                   ui.NORMAL, 'for transaction fee?',
                   icon_color=ui.GREEN)
    await require_hold_to_confirm(ctx, content, ButtonRequestType.SignTx)  # we use SignTx, not ConfirmOutput, for compatibility with T1


async def require_confirm_payload(ctx, payload: bytes, encrypt=False):
    payload = str(payload, 'utf-8')

    if len(payload) > 48:
        payload = payload[:48] + '..'
    if encrypt:
        content = Text('Confirm payload', ui.ICON_SEND,
                       ui.BOLD, 'Encrypted:',
                       ui.NORMAL, *split_words(payload, 22),
                       icon_color=ui.GREEN)
    else:
        content = Text('Confirm payload', ui.ICON_SEND,
                       ui.BOLD, 'Unencrypted:',
                       ui.NORMAL, *split_words(payload, 22),
                       icon_color=ui.RED)
    await require_confirm(ctx, content, ButtonRequestType.ConfirmOutput)


async def require_confirm_properties(ctx, definition: NEMMosaicDefinition):
    properties = _get_mosaic_properties(definition)
    first_page = const(0)
    paginator = paginate(_show_page, len(properties), first_page, properties)
    await ctx.wait(paginator)


@ui.layout
async def _show_page(page: int, page_count: int, content):
    content = Scrollpage(content[page], page, page_count)
    if page + 1 == page_count:
        await ConfirmDialog(content)
    else:
        content.render()
        await animate_swipe()


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
                 ui.NORMAL, str(definition.supply),
                 ui.NORMAL, imm)
    else:
        t = Text('Confirm properties', ui.ICON_SEND,
                 ui.BOLD, 'Initial supply:',
                 ui.NORMAL, imm)
    properties.append(t)
    if definition.levy:
        t = Text('Confirm properties', ui.ICON_SEND,
                 ui.BOLD, 'Levy recipient:',
                 ui.MONO, *split_address(definition.levy_address))
        properties.append(t)
        t = Text('Confirm properties', ui.ICON_SEND,
                 ui.BOLD, 'Levy namespace:',
                 ui.NORMAL, definition.levy_namespace,
                 ui.BOLD, 'Levy mosaic:',
                 ui.NORMAL, definition.levy_mosaic)
        properties.append(t)
        if definition.levy == NEMMosaicLevy.MosaicLevy_Absolute:
            levy_type = 'absolute'
        else:
            levy_type = 'percentile'
        t = Text('Confirm properties', ui.ICON_SEND,
                 ui.BOLD, 'Levy type:',
                 ui.NORMAL, levy_type)
        properties.append(t)

    return properties


def split_address(data):
    return chunks(data, 17)
