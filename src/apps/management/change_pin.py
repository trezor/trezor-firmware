from trezor import ui
from trezor import config
from trezor.pin import pin_to_int
from trezor.utils import unimport


async def request_pin(ctx):
    from trezor.messages.ButtonRequest import ButtonRequest
    from trezor.messages.wire_types import ButtonAck
    from apps.common.request_pin import request_pin

    await ctx.call(ButtonRequest(), ButtonAck)

    return await request_pin()


async def request_pin_confirm(ctx):
    while True:
        pin1 = await request_pin(ctx)
        pin2 = await request_pin(ctx)
        if pin1 == pin2:
            return pin1
        # TODO: display a message and wait


def confirm_change_pin(ctx, msg):
    from apps.common.confirm import require_confirm
    from trezor.ui.text import Text

    has_pin = config.has_pin()

    if msg.remove and has_pin:  # removing pin
        return require_confirm(ctx, Text(
            'Remove PIN', ui.ICON_RESET,
            'Do you really want to', ui.BOLD,
            'remove current PIN?'))

    if not msg.remove and has_pin:  # changing pin
        return require_confirm(ctx, Text(
            'Change PIN', ui.ICON_RESET,
            'Do you really want to', ui.BOLD,
            'change current PIN?'))

    if not msg.remove and not has_pin:  # setting new pin
        return require_confirm(ctx, Text(
            'Change PIN', ui.ICON_RESET,
            'Do you really want to', ui.BOLD,
            'set new PIN?'))


@unimport
async def layout_change_pin(ctx, msg):
    from trezor.messages.Success import Success
    from trezor.messages.Failure import Failure
    from trezor.messages.FailureType import PinInvalid
    from apps.common.request_pin import show_pin_timeout

    await confirm_change_pin(ctx, msg)

    if config.has_pin():
        curr_pin = await request_pin(ctx)
    else:
        curr_pin = ''
    if msg.remove:
        new_pin = ''
    else:
        new_pin = await request_pin_confirm(ctx)

    if config.change_pin(pin_to_int(curr_pin), pin_to_int(new_pin), show_pin_timeout):
        if new_pin:
            return Success(message='PIN changed')
        else:
            return Success(message='PIN removed')
    else:
        return Failure(code=PinInvalid, message='PIN invalid')
