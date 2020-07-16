from trezor import ui, utils, workflow

_progress = 0
_steps = 0


def init(inputs: int, outputs: int) -> None:
    global _progress, _steps
    _progress = 0
    _steps = inputs + inputs + outputs + inputs
    report_init()
    report()


def advance(i: int = 1) -> None:
    global _progress
    _progress += i
    report()


def report_init() -> None:
    workflow.close_others()
    ui.display.clear()
    ui.header("Signing transaction")


def report() -> None:
    if utils.DISABLE_ANIMATION:
        return
    p = 1000 * _progress // _steps
    ui.display.loader(p, False, 18, ui.WHITE, ui.BG)
