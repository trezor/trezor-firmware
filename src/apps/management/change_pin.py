from trezor import config, loop, ui, wire
from trezor.messages import ButtonRequestType, MessageType
from trezor.messages.ButtonRequest import ButtonRequest
from trezor.messages.Success import Success
from trezor.pin import pin_to_int, show_pin_timeout
from trezor.ui.text import Text

from apps.common.confirm import require_confirm
from apps.common.request_pin import PinCancelled, request_pin


async def change_pin(ctx, msg):

    # confirm that user wants to change the pin
    await require_confirm_change_pin(ctx, msg)

    # get current pin, return failure if invalid
    if config.has_pin():
        curpin = await request_pin_ack(ctx)
        if not config.check_pin(pin_to_int(curpin), show_pin_timeout):
            raise wire.PinInvalid("PIN invalid")
    else:
        curpin = ""

    # get new pin
    if not msg.remove:
        newpin = await request_pin_confirm(ctx)
    else:
        newpin = ""

    # write into storage
    if not config.change_pin(pin_to_int(curpin), pin_to_int(newpin), show_pin_timeout):
        raise wire.PinInvalid("PIN invalid")

    if newpin:
        return Success(message="PIN changed")
    else:
        return Success(message="PIN removed")


def require_confirm_change_pin(ctx, msg):
    has_pin = config.has_pin()

    if msg.remove and has_pin:  # removing pin
        text = Text("Remove PIN", ui.ICON_CONFIG)
        text.normal("Do you really want to")
        text.bold("remove current PIN?")
        return require_confirm(ctx, text)

    if not msg.remove and has_pin:  # changing pin
        text = Text("Remove PIN", ui.ICON_CONFIG)
        text.normal("Do you really want to")
        text.bold("change current PIN?")
        return require_confirm(ctx, text)

    if not msg.remove and not has_pin:  # setting new pin
        text = Text("Remove PIN", ui.ICON_CONFIG)
        text.normal("Do you really want to")
        text.bold("set new PIN?")
        return require_confirm(ctx, text)


async def request_pin_confirm(ctx, *args, **kwargs):
    while True:
        pin1 = await request_pin_ack(ctx, "Enter new PIN", *args, **kwargs)
        pin2 = await request_pin_ack(ctx, "Re-enter new PIN", *args, **kwargs)
        if pin1 == pin2:
            return pin1
        await pin_mismatch()


async def request_pin_ack(ctx, *args, **kwargs):
    try:
        await ctx.call(
            ButtonRequest(code=ButtonRequestType.Other), MessageType.ButtonAck
        )
        return await ctx.wait(request_pin(*args, **kwargs))
    except PinCancelled:
        raise wire.ActionCancelled("Cancelled")


@ui.layout
async def pin_mismatch():
    text = Text("PIN mismatch", ui.ICON_WRONG, icon_color=ui.RED)
    text.normal("Entered PINs do not", "match each other.")
    text.normal("")
    text.normal("Please, try again...")
    text.render()
    await loop.sleep(3 * 1000 * 1000)
