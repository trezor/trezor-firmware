from trezor import config, loop, res, ui
from trezor.pin import pin_to_int, show_pin_timeout

from apps.common.request_pin import request_pin


async def bootscreen():
    while True:
        try:
            if not config.has_pin():
                config.unlock(pin_to_int(""), show_pin_timeout)
                return
            await lockscreen()
            label = None
            while True:
                pin = await request_pin(label)
                if config.unlock(pin_to_int(pin), show_pin_timeout):
                    return
                else:
                    label = "Wrong PIN, enter again"
        except:  # noqa: E722
            pass


async def lockscreen():
    from apps.common import storage

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


config.init()
ui.display.backlight(ui.BACKLIGHT_NONE)
loop.schedule(bootscreen())
loop.run()
