from trezor import ui


def pin_to_int(pin: str) -> int:
    return int("1" + pin)


def show_pin_timeout(seconds: int, progress: int):
    if progress == 0:
        ui.display.bar(0, 0, ui.WIDTH, ui.HEIGHT, ui.BG)
        ui.display.text_center(
            ui.WIDTH // 2, 37, "Verifying PIN", ui.BOLD, ui.FG, ui.BG, ui.WIDTH
        )
    ui.display.loader(progress, 0, ui.FG, ui.BG)
    if seconds == 0:
        ui.display.text_center(
            ui.WIDTH // 2, ui.HEIGHT - 22, "Done", ui.BOLD, ui.FG, ui.BG, ui.WIDTH
        )
    elif seconds == 1:
        ui.display.text_center(
            ui.WIDTH // 2,
            ui.HEIGHT - 22,
            "1 second left",
            ui.BOLD,
            ui.FG,
            ui.BG,
            ui.WIDTH,
        )
    else:
        ui.display.text_center(
            ui.WIDTH // 2,
            ui.HEIGHT - 22,
            "%d seconds left" % seconds,
            ui.BOLD,
            ui.FG,
            ui.BG,
            ui.WIDTH,
        )
    ui.display.refresh()
