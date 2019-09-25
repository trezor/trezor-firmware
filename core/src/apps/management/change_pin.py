from trezor import config, ui, wire
from trezor.messages.Success import Success
from trezor.pin import pin_to_int
from trezor.ui.text import Text

from apps.common.confirm import require_confirm
from apps.common.request_pin import request_pin_and_sd_salt, request_pin_confirm

if False:
    from trezor.messages.ChangePin import ChangePin


async def change_pin(ctx: wire.Context, msg: ChangePin) -> Success:
    # confirm that user wants to change the pin
    await require_confirm_change_pin(ctx, msg)

    # get old pin
    curpin, salt = await request_pin_and_sd_salt(ctx, "Enter old PIN")

    # if changing pin, pre-check the entered pin before getting new pin
    if curpin and not msg.remove:
        if not config.check_pin(pin_to_int(curpin), salt):
            raise wire.PinInvalid("PIN invalid")

    # get new pin
    if not msg.remove:
        newpin = await request_pin_confirm(ctx)
    else:
        newpin = ""

    # write into storage
    if not config.change_pin(pin_to_int(curpin), pin_to_int(newpin), salt, salt):
        raise wire.PinInvalid("PIN invalid")

    if newpin:
        return Success(message="PIN changed")
    else:
        return Success(message="PIN removed")


def require_confirm_change_pin(ctx: wire.Context, msg: ChangePin) -> None:
    has_pin = config.has_pin()

    if msg.remove and has_pin:  # removing pin
        text = Text("Remove PIN", ui.ICON_CONFIG)
        text.normal("Do you really want to")
        text.bold("disable PIN protection?")
        return require_confirm(ctx, text)

    if not msg.remove and has_pin:  # changing pin
        text = Text("Change PIN", ui.ICON_CONFIG)
        text.normal("Do you really want to")
        text.bold("change your PIN?")
        return require_confirm(ctx, text)

    if not msg.remove and not has_pin:  # setting new pin
        text = Text("Enable PIN", ui.ICON_CONFIG)
        text.normal("Do you really want to")
        text.bold("enable PIN protection?")
        return require_confirm(ctx, text)

    # removing non-existing PIN
    raise wire.ProcessError("PIN protection already disabled")
