from trezor import ui

_progress = 0
_steps = 0


def init(total_steps: int, text: str) -> None:
    global _progress, _steps
    _progress = 0
    _steps = total_steps
    report_init(text)
    report()


def advance() -> None:
    global _progress
    _progress += 1
    report()


def report_init(text: str) -> None:
    ui.display.clear()
    ui.header(text)


def report() -> None:
    p = 1000 * _progress // _steps
    ui.display.loader(p, False, 18, ui.WHITE, ui.BG)
