from trezor import config, io, loop, res, ui

from apps.common import storage


async def homescreen():
    # render homescreen in dimmed mode and fade back in
    ui.backlight_fade(ui.BACKLIGHT_DIM)
    display_homescreen()
    ui.backlight_fade(ui.BACKLIGHT_NORMAL)

    # loop forever, never return
    touch = loop.wait(io.TOUCH)
    while True:
        await touch


def display_homescreen():
    image = None
    if storage.slip39.is_in_progress():
        label = "Waiting for other shares"
    elif not storage.is_initialized():
        label = "Go to trezor.io/start"
    else:
        label = storage.device.get_label() or "My Trezor"
        image = storage.device.get_homescreen()

    if not image:
        image = res.load("apps/homescreen/res/bg.toif")

    if storage.is_initialized() and storage.device.no_backup():
        _err("SEEDLESS")
    elif storage.is_initialized() and storage.device.unfinished_backup():
        _err("BACKUP FAILED!")
    elif storage.is_initialized() and storage.device.needs_backup():
        _warn("NEEDS BACKUP!")
    elif storage.is_initialized() and not config.has_pin():
        _warn("PIN NOT SET!")
    elif storage.slip39.is_in_progress():
        _warn("SHAMIR IN PROGRESS!")
    else:
        ui.display.bar(0, 0, ui.WIDTH, ui.HEIGHT, ui.BG)
    ui.display.avatar(48, 48 - 10, image, ui.WHITE, ui.BLACK)
    ui.display.text_center(ui.WIDTH // 2, 220, label, ui.BOLD, ui.FG, ui.BG)


def _warn(message: str):
    ui.display.bar(0, 0, ui.WIDTH, 30, ui.YELLOW)
    ui.display.text_center(ui.WIDTH // 2, 22, message, ui.BOLD, ui.BLACK, ui.YELLOW)
    ui.display.bar(0, 30, ui.WIDTH, ui.HEIGHT - 30, ui.BG)


def _err(message: str):
    ui.display.bar(0, 0, ui.WIDTH, 30, ui.RED)
    ui.display.text_center(ui.WIDTH // 2, 22, message, ui.BOLD, ui.WHITE, ui.RED)
    ui.display.bar(0, 30, ui.WIDTH, ui.HEIGHT - 30, ui.BG)
