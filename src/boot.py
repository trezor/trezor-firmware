from trezor import config, loop, res, ui
from trezor.pin import pin_to_int, show_pin_timeout
from apps.common.request_pin import request_pin


async def bootscreen():
    while True:
        try:
            if not config.has_pin():
                config.unlock(pin_to_int(''), show_pin_timeout)
                return
            await lockscreen()
            while True:
                pin = await request_pin()
                if config.unlock(pin_to_int(pin), show_pin_timeout):
                    return
        except:  # noqa: E722
            pass


async def lockscreen():
    from apps.common import storage

    label = storage.get_label()
    image = storage.get_homescreen()
    if not label:
        label = 'My TREZOR'
    if not image:
        image = res.load('apps/homescreen/res/bg.toif')

    await ui.backlight_slide(ui.BACKLIGHT_DIM)

    ui.display.bar(0, 0, 240, 240, ui.WHITE)
    ui.display.avatar(48, 48, image, ui.BLACK, ui.WHITE)
    ui.display.text_center(120, 35, label, ui.BOLD, ui.BLACK, ui.WHITE)

    ui.display.text_center(130, 220, 'Tap to unlock', ui.BOLD, ui.DARK_GREY, ui.WHITE)
    ui.display.icon(45, 202, res.load(ui.ICON_CLICK), ui.DARK_GREY, ui.WHITE)

    await ui.backlight_slide(ui.BACKLIGHT_NORMAL)
    await ui.click()


config.init()
ui.display.backlight(ui.BACKLIGHT_NONE)
loop.schedule(bootscreen())
loop.run()
