from trezor import ui


async def layout_wipe_device(ctx, msg):
    from trezor.messages.Success import Success
    from trezor.ui.text import Text
    from ..common.confirm import hold_to_confirm
    from ..common import storage

    await hold_to_confirm(ctx, Text(
        'Wipe device',
        ui.ICON_WIPE,
        ui.NORMAL, 'Do you really want to', 'wipe the device?',
        ui.NORMAL, '', 'All data will be lost.',
        icon_color=ui.RED),
        button_style=ui.BTN_CANCEL,
        loader_style=ui.LDR_DANGER)

    storage.wipe()

    return Success(message='Device wiped')
