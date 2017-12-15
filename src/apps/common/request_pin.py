from trezor import res
from trezor import ui


class PinCancelled(Exception):
    pass


@ui.layout
async def request_pin(code: int = None) -> str:
    from trezor.ui.confirm import ConfirmDialog, CONFIRMED
    from trezor.ui.pin import PinMatrix

    label = _get_label(code)

    def onchange():
        c = dialog.cancel
        if matrix.pin:
            c.content = res.load(ui.ICON_CLEAR)
        else:
            c.content = res.load(ui.ICON_LOCK)
        c.taint()
        c.render()

    ui.display.clear()
    matrix = PinMatrix(label, with_zero=True)
    matrix.onchange = onchange
    dialog = ConfirmDialog(matrix)
    dialog.cancel.area = (0, 240 - 48, 80, 48)
    dialog.confirm.area = (240 - 80, 240 - 48, 80, 48)
    matrix.onchange()

    while True:
        result = await dialog

        if result == CONFIRMED:
            return matrix.pin
        elif result != CONFIRMED and matrix.pin:
            matrix.change('')
            continue
        else:
            raise PinCancelled()


def _get_label(code: int):
    from trezor.messages import PinMatrixRequestType
    if code is None:
        code = PinMatrixRequestType.Current
    if code == PinMatrixRequestType.NewFirst:
        label = 'Enter new PIN'
    elif code == PinMatrixRequestType.NewSecond:
        label = 'Enter PIN again'
    else:  # PinMatrixRequestType.Current
        label = 'Enter PIN'
    return label
