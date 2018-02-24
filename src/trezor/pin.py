from trezor import ui


def pin_to_int(pin: str) -> int:
    return int('1' + pin)


def show_pin_timeout(seconds: int, progress: int):
    if progress == 0:
        ui.display.bar(0, 0, ui.WIDTH, ui.HEIGHT, ui.BG)
    ui.display.loader(progress, -10, ui.FG, ui.BG)
    if seconds == 0:
        ui.display.text_center(ui.WIDTH // 2, ui.HEIGHT - 20, 'Done', ui.BOLD, ui.FG, ui.BG, ui.WIDTH)
    else:
        ui.display.text_center(ui.WIDTH // 2, ui.HEIGHT - 20, 'Waiting for %d s' % seconds, ui.BOLD, ui.FG, ui.BG, ui.WIDTH)
    ui.display.refresh()
