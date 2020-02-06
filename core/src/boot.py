import storage
import storage.device
import storage.sd_salt
from trezor import config, io, log, loop, res, ui, utils
from trezor.pin import pin_to_int, show_pin_timeout
from trezor.ui.confirm import HoldToConfirm
from trezor.ui.text import Text

from apps.common.request_pin import PinCancelled, request_pin
from apps.common.sd_salt import SdProtectCancelled, request_sd_salt


async def assert_sdcard() -> None:
    sd = io.SDCard()
    if not sd.present():
        return

    sd.power(True)
    fs = io.FatFS()
    try:
        fs.mount()
    except OSError:
        text = Text("SD card", ui.ICON_WRONG, ui.RED)
        text.normal("Unrecognized filesystem")
        text.normal("found. Unplug the device")
        text.normal("and remove the card or")
        text.normal("you can format the card")
        text.normal("losing all the data on it.")
        dialog = HoldToConfirm(text, confirm="Format SD card")
        await dialog
        fs.mkfs()
        fs.setlabel("TREZOR")
    else:
        fs.unmount()
    sd.power(False)


async def bootscreen() -> None:
    ui.display.orientation(storage.device.get_rotation())

    await assert_sdcard()

    while True:
        try:
            if storage.sd_salt.is_enabled() or config.has_pin():
                await lockscreen()

            salt = await request_sd_salt()

            if not config.has_pin():
                config.unlock(pin_to_int(""), salt)
                storage.init_unlocked()
                return

            label = "Enter your PIN"
            while True:
                pin = await request_pin(label, config.get_pin_rem())
                if config.unlock(pin_to_int(pin), salt):
                    storage.init_unlocked()
                    return
                else:
                    label = "Wrong PIN, enter again"
        except (OSError, PinCancelled, SdProtectCancelled) as e:
            if __debug__:
                log.exception(__name__, e)
        except BaseException as e:
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
