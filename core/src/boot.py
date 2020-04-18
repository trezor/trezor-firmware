import storage
import storage.device
import storage.sd_salt
from trezor import config, log, loop, res, ui, utils
from trezor.pin import show_pin_timeout

from apps.common.request_pin import PinCancelled, verify_user_pin


async def bootscreen() -> None:
    ui.display.orientation(storage.device.get_rotation())
    while True:
        try:
            if storage.sd_salt.is_enabled() or config.has_pin():
                await lockscreen()
            await verify_user_pin()
            storage.init_unlocked()
            return
        except PinCancelled as e:
            # verify_user_pin will convert a SdCardUnavailable (in case of sd salt)
            # to PinCancelled exception.
            # log the exception and retry loop
            if __debug__:
                log.exception(__name__, e)
        except BaseException as e:
            # other exceptions here are unexpected and should halt the device
            if __debug__:
                log.exception(__name__, e)
            utils.halt(e.__class__.__name__)


async def lockscreen() -> None:
    label = storage.device.get_label()
    image = storage.device.get_homescreen()
    if not label:
        label = "My Trezor"
    if not image:
        image = res.load("apps/homescreen/res/bg.toif")

    ui.backlight_fade(ui.BACKLIGHT_DIM)

    ui.display.clear()
    ui.display.avatar(48, 48, image, ui.TITLE_GREY, ui.BG)
    ui.display.text_center(ui.WIDTH // 2, 35, label, ui.BOLD, ui.TITLE_GREY, ui.BG)

    ui.display.bar_radius(40, 100, 160, 40, ui.TITLE_GREY, ui.BG, 4)
    ui.display.bar_radius(42, 102, 156, 36, ui.BG, ui.TITLE_GREY, 4)
    ui.display.text_center(ui.WIDTH // 2, 128, "Locked", ui.BOLD, ui.TITLE_GREY, ui.BG)

    ui.display.text_center(
        ui.WIDTH // 2 + 10, 220, "Tap to unlock", ui.BOLD, ui.TITLE_GREY, ui.BG
    )
    ui.display.icon(45, 202, res.load(ui.ICON_CLICK), ui.TITLE_GREY, ui.BG)

    ui.backlight_fade(ui.BACKLIGHT_NORMAL)

    await ui.click()


ui.display.backlight(ui.BACKLIGHT_NONE)
ui.backlight_fade(ui.BACKLIGHT_NORMAL)
config.init(show_pin_timeout)
loop.schedule(bootscreen())
loop.run()
