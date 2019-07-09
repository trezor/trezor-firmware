from trezor import config, ui, wire
from trezor.messages import ButtonRequestType
from trezor.messages.ButtonAck import ButtonAck
from trezor.messages.ButtonRequest import ButtonRequest
from trezor.messages.Success import Success
from trezor.pin import pin_to_int
from trezor.ui.popup import Popup
from trezor.ui.text import Text

from apps.common.confirm import require_confirm
from apps.common.request_pin import PinCancelled, request_pin


async def change_pin(ctx, msg):

    # confirm that user wants to change the pin
    await require_confirm_change_pin(ctx, msg)

    # get current pin, return failure if invalid
    if config.has_pin():
        curpin = await request_pin_ack(ctx, "Enter old PIN", config.get_pin_rem())
        # if removing, defer check to change_pin()
        if not msg.remove:
            if not config.check_pin(pin_to_int(curpin)):
                raise wire.PinInvalid("PIN invalid")
    else:
        curpin = ""

    # get new pin
    if not msg.remove:
        newpin = await request_pin_confirm(ctx)
    else:
        newpin = ""

    # write into storage
    if not config.change_pin(pin_to_int(curpin), pin_to_int(newpin)):
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
        text.bold("disable PIN protection?")
        return require_confirm(ctx, text)

    if not msg.remove and has_pin:  # changing pin
        text = Text("Change PIN", ui.ICON_CONFIG)
        text.normal("Do you really want to")
        text.bold("change the current PIN?")
        return require_confirm(ctx, text)

    if not msg.remove and not has_pin:  # setting new pin
        text = Text("Enable PIN", ui.ICON_CONFIG)
        text.normal("Do you really want to")
        text.bold("enable PIN protection?")
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
        await ctx.call(ButtonRequest(code=ButtonRequestType.Other), ButtonAck)
        return await ctx.wait(request_pin(*args, **kwargs))
    except PinCancelled:
        raise wire.ActionCancelled("Cancelled")


async def pin_mismatch():
    text = Text("PIN mismatch", ui.ICON_WRONG, ui.RED)
    text.normal("Entered PINs do not", "match each other.")
    text.normal("")
    text.normal("Please, try again...")
    popup = Popup(text, 3000)  # show for 3 seconds
    await popup
