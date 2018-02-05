from trezor import ui


def pin_to_int(pin: str) -> int:
    return int('1' + pin)


def show_pin_timeout(wait: int, total: int):
    ui.display.bar(0, 0, ui.SCREEN, ui.SCREEN, ui.BG)
    ui.display.loader(1000 - (1000 * wait // total), -10, ui.FG, ui.BG)
    ui.display.text_center(ui.SCREEN // 2, ui.SCREEN - 20, 'Waiting for %d s' % wait, ui.BOLD, ui.FG, ui.BG)
    ui.display.refresh()
