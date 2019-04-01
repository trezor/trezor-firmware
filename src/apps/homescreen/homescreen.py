from trezor import config, res, ui

from apps.common import storage


async def homescreen():
    await ui.backlight_slide(ui.BACKLIGHT_DIM)
    display_homescreen()
    await ui.backlight_slide(ui.BACKLIGHT_NORMAL)


def display_homescreen():
    if not storage.is_initialized():
        label = "Go to trezor.io/start"
        image = None
    else:
        label = storage.get_label() or "My TREZOR"
        image = storage.get_homescreen()

    if not image:
        image = res.load("apps/homescreen/res/bg.toif")

    if storage.is_initialized() and storage.no_backup():
        ui.display.bar(0, 0, ui.WIDTH, 30, ui.RED)
        ui.display.text_center(ui.WIDTH // 2, 22, "SEEDLESS", ui.BOLD, ui.WHITE, ui.RED)
        ui.display.bar(0, 30, ui.WIDTH, ui.HEIGHT - 30, ui.BG)
    elif storage.is_initialized() and storage.unfinished_backup():
        ui.display.bar(0, 0, ui.WIDTH, 30, ui.RED)
        ui.display.text_center(
            ui.WIDTH // 2, 22, "BACKUP FAILED!", ui.BOLD, ui.WHITE, ui.RED
        )
        ui.display.bar(0, 30, ui.WIDTH, ui.HEIGHT - 30, ui.BG)
    elif storage.is_initialized() and storage.needs_backup():
        ui.display.bar(0, 0, ui.WIDTH, 30, ui.YELLOW)
        ui.display.text_center(
            ui.WIDTH // 2, 22, "NEEDS BACKUP!", ui.BOLD, ui.BLACK, ui.YELLOW
        )
        ui.display.bar(0, 30, ui.WIDTH, ui.HEIGHT - 30, ui.BG)
    elif storage.is_initialized() and not config.has_pin():
        ui.display.bar(0, 0, ui.WIDTH, 30, ui.YELLOW)
        ui.display.text_center(
            ui.WIDTH // 2, 22, "PIN NOT SET!", ui.BOLD, ui.BLACK, ui.YELLOW
        )
        ui.display.bar(0, 30, ui.WIDTH, ui.HEIGHT - 30, ui.BG)
    else:
        ui.display.bar(0, 0, ui.WIDTH, ui.HEIGHT, ui.BG)
    ui.display.avatar(48, 48 - 10, image, ui.WHITE, ui.BLACK)
    ui.display.text_center(ui.WIDTH // 2, 220, label, ui.BOLD, ui.FG, ui.BG)
