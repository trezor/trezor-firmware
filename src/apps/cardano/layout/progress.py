from trezor import ui

_progress = 0
_steps = 0


def init(total_steps, text):
    global _progress, _steps
    _progress = 0
    _steps = total_steps
    report_init(text)
    report()


def advance():
    global _progress
    _progress += 1
    report()


def report_init(text):
    ui.display.clear()
    ui.header(text)


def report():
    p = int(1000 * _progress / _steps)
    ui.display.loader(p, 18, ui.WHITE, ui.BG)
