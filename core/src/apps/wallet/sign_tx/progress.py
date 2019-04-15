from trezor import ui

_progress = 0
_steps = 0


def init(inputs, outputs):
    global _progress, _steps
    _progress = 0
    _steps = inputs + inputs + outputs + inputs
    report_init()
    report()


def advance():
    global _progress
    _progress += 1
    report()


def report_init():
    ui.display.clear()
    ui.header("Signing transaction")


def report():
    p = int(1000 * _progress / _steps)
    ui.display.loader(p, 18, ui.WHITE, ui.BG)
