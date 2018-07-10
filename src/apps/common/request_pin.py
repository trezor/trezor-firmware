from trezor import loop, res, ui
from trezor.ui.confirm import CONFIRMED, ConfirmDialog
from trezor.ui.pin import PinMatrix

if __debug__:
    from apps.debug import input_signal


class PinCancelled(Exception):
    pass


@ui.layout
async def request_pin(label=None, cancellable: bool = True) -> str:
    def onchange():
        c = dialog.cancel
        if matrix.pin:
            back = res.load(ui.ICON_BACK)
            if c.content is not back:
                c.normal_style = ui.BTN_CLEAR["normal"]
                c.content = back
                c.enable()
                c.taint()
        else:
            lock = res.load(ui.ICON_LOCK)
            if not cancellable and c.content:
                c.content = ""
                c.disable()
                c.taint()
            elif c.content is not lock:
                c.normal_style = ui.BTN_CANCEL["normal"]
                c.content = lock
                c.enable()
                c.taint()
        c.render()

    if label is None:
        label = "Enter your PIN"
    matrix = PinMatrix(label)
    matrix.onchange = onchange
    dialog = ConfirmDialog(matrix)
    dialog.cancel.area = ui.grid(12)
    dialog.confirm.area = ui.grid(14)
    matrix.onchange()

    while True:
        if __debug__:
            result = await loop.spawn(dialog, input_signal)
            if isinstance(result, str):
                return result
        else:
            result = await dialog
        if result == CONFIRMED:
            return matrix.pin
        elif matrix.pin:  # reset
            matrix.change("")
            continue
        else:  # cancel
            raise PinCancelled()
