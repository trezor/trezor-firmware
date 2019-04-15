from trezor import config, log, loop, res, ui
from trezor.pin import pin_to_int, show_pin_timeout

from apps.common import storage
from apps.common.request_pin import request_pin


async def bootscreen():
    ui.display.orientation(storage.get_rotation())
    while True:
        try:
            if not config.has_pin():
                config.unlock(pin_to_int(""))
                storage.init_unlocked()
                return
            await lockscreen()
            label = None
            while True:
                pin = await request_pin(label, config.get_pin_rem())
                if config.unlock(pin_to_int(pin)):
                    storage.init_unlocked()
                    return
                else:
                    label = "Wrong PIN, enter again"
        except Exception as e:
            if __debug__:
                log.exception(__name__, e)


async def lockscreen():
    label = storage.get_label()
    image = storage.get_homescreen()
    if not label:
        label = "My TREZOR"
    if not image:
        image = res.load("apps/homescreen/res/bg.toif")

    await ui.backlight_slide(ui.BACKLIGHT_DIM)

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

    await ui.backlight_slide(ui.BACKLIGHT_NORMAL)
    await ui.click()


ui.display.backlight(ui.BACKLIGHT_NONE)
ui.backlight_slide_sync(ui.BACKLIGHT_NORMAL)
config.init(show_pin_timeout)
loop.schedule(bootscreen())
loop.run()
