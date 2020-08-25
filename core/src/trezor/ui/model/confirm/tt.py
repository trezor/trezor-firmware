from trezor import res, ui

from ..button import ButtonCancel, ButtonConfirm

if False:
    from typing import Union

DEFAULT_CONFIRM = res.load(ui.ICON_CONFIRM)  # type: Union[bytes, str]
DEFAULT_CONFIRM_STYLE = ButtonConfirm
DEFAULT_CANCEL = res.load(ui.ICON_CANCEL)  # type: Union[bytes, str]
DEFAULT_CANCEL_STYLE = ButtonCancel


def confirm_button_area(
    is_right: bool, only_one: bool = False, major_confirm: bool = False
) -> ui.Area:
    if is_right:
        if only_one:
            return ui.grid(4, n_x=1)
        elif major_confirm:
            return ui.grid(13, cells_x=2)
        else:
            return ui.grid(9, n_x=2)
    else:
        if only_one:
            return ui.grid(4, n_x=1)
        elif major_confirm:
            return ui.grid(12, cells_x=1)
        else:
            return ui.grid(8, n_x=2)
