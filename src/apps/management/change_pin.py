from trezor import ui
from trezor.utils import unimport


def confirm_set_pin(ctx):
    from apps.common.confirm import require_confirm
    from trezor.ui.text import Text
    return require_confirm(ctx, Text(
        'Change PIN', ui.ICON_RESET,
        'Do you really want to', ui.BOLD,
        'set new PIN?'))


def confirm_change_pin(ctx):
    from apps.common.confirm import require_confirm
    from trezor.ui.text import Text
    return require_confirm(ctx, Text(
        'Change PIN', ui.ICON_RESET,
        'Do you really want to', ui.BOLD,
        'change current PIN?'))


def confirm_remove_pin(ctx):
    from apps.common.confirm import require_confirm
    from trezor.ui.text import Text
    return require_confirm(ctx, Text(
        'Remove PIN', ui.ICON_RESET,
        'Do you really want to', ui.BOLD,
        'remove current PIN?'))


@unimport
async def layout_change_pin(ctx, msg):
    from trezor.messages.Success import Success
    from apps.common.request_pin import protect_by_pin, request_pin_twice
    from apps.common import storage

    if msg.remove:
        if storage.is_protected_by_pin():
            await confirm_remove_pin(ctx)
            await protect_by_pin(ctx, at_least_once=True)
        pin = ''

    else:
        if storage.is_protected_by_pin():
            await confirm_change_pin(ctx)
            await protect_by_pin(ctx, at_least_once=True)
        else:
            await confirm_set_pin(ctx)
        pin = await request_pin_twice(ctx)

    storage.load_settings(pin=pin)
    if pin:
        storage.lock()
        return Success(message='PIN changed')
    else:
        return Success(message='PIN removed')
