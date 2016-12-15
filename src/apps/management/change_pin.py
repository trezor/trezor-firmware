from trezor import ui
from trezor.utils import unimport


def confirm_set_pin(session_id):
    from apps.common.confirm import require_confirm
    from trezor.ui.text import Text
    return require_confirm(session_id, Text(
        'Change PIN', ui.ICON_RESET,
        'Do you really want to', ui.BOLD,
        'set new PIN?'))


def confirm_change_pin(session_id):
    from apps.common.confirm import require_confirm
    from trezor.ui.text import Text
    return require_confirm(session_id, Text(
        'Change PIN', ui.ICON_RESET,
        'Do you really want to', ui.BOLD,
        'change current PIN?'))


def confirm_remove_pin(session_id):
    from apps.common.confirm import require_confirm
    from trezor.ui.text import Text
    return require_confirm(session_id, Text(
        'Remove PIN', ui.ICON_RESET,
        'Do you really want to', ui.BOLD,
        'remove current PIN?'))


@unimport
async def layout_change_pin(session_id, msg):
    from trezor.messages.Success import Success
    from ..common.request_pin import protect_by_pin, request_pin_twice
    from ..common import storage

    if msg.remove:
        if storage.is_protected_by_pin():
            await confirm_remove_pin(session_id)
            await protect_by_pin(session_id)
        storage.load_settings(pin='')
        return Success(message='PIN removed')

    else:
        if storage.is_protected_by_pin():
            await confirm_change_pin(session_id)
            await protect_by_pin(session_id)
        else:
            await confirm_set_pin(session_id)
        pin = await request_pin_twice(session_id)
        storage.load_settings(pin=pin)
        return Success(message='PIN changed')
