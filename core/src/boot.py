from trezor import config, io, log, loop, res, ui, utils
from trezor.pin import pin_to_int, show_pin_timeout

from apps.common import storage
from apps.common.request_pin import PinCancelled, request_pin
from apps.common.sd_salt import SdProtectCancelled, request_sd_salt
from apps.common.storage import device

if False:
    from typing import Optional


async def bootscreen() -> None:
    ui.display.orientation(storage.device.get_rotation())
    salt_auth_key = device.get_sd_salt_auth_key()

    while True:
        try:
            if salt_auth_key is not None or config.has_pin():
                await lockscreen()

            if salt_auth_key is not None:
                salt = await request_sd_salt(
                    None, salt_auth_key
                )  # type: Optional[bytearray]
            else:
                salt = None

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
        except Exception as e:
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


if utils.EMULATOR:
    # Ensure the emulated SD card is FAT32 formatted.
    sd = io.SDCard()
    sd.power(True)
    fs = io.FatFS()
    try:
        fs.mount()
    except OSError:
        fs.mkfs()
    else:
        fs.unmount()
    sd.power(False)

ui.display.backlight(ui.BACKLIGHT_NONE)
ui.backlight_fade(ui.BACKLIGHT_NORMAL)
config.init(show_pin_timeout)
loop.schedule(bootscreen())
loop.run()
