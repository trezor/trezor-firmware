from trezor import ui

from ..button import ButtonCancel, ButtonConfirm

if False:
    from typing import Union

DEFAULT_CONFIRM = "CONFIRM"  # type: Union[bytes, str]
DEFAULT_CONFIRM_STYLE = ButtonConfirm
DEFAULT_CANCEL = "CANCEL"  # type: Union[bytes, str]
DEFAULT_CANCEL_STYLE = ButtonCancel


def confirm_button_area(
    is_right: bool, only_one: bool = False, major_confirm: bool = False
) -> ui.Area:
    if is_right:
        if only_one or major_confirm:
            return (ui.WIDTH // 3, ui.HEIGHT - 11, 2 * ui.WIDTH // 3, 11)
        else:
            return (ui.WIDTH // 2, ui.HEIGHT - 11, ui.WIDTH // 2, 11)
    else:
        if only_one or major_confirm:
            return (0, ui.HEIGHT - 11, 2 * ui.WIDTH // 3, 11)
        else:
            return (0, ui.HEIGHT - 11, ui.WIDTH // 2, 11)
