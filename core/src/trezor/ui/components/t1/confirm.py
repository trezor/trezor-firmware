from trezor import ui

from ..common.confirm import ConfirmBase
from .button import Button, ButtonBlack, ButtonWhite

if False:
    from typing import Optional
    from .button import ButtonContent, ButtonStyleType


class Confirm(ConfirmBase):
    DEFAULT_CONFIRM = "CONFIRM"
    DEFAULT_CONFIRM_STYLE = ButtonWhite
    DEFAULT_CANCEL = "CANCEL"
    DEFAULT_CANCEL_STYLE = ButtonBlack

    def __init__(
        self,
        content: ui.Component,
        confirm: Optional[ButtonContent] = DEFAULT_CONFIRM,
        confirm_style: ButtonStyleType = DEFAULT_CONFIRM_STYLE,
        cancel: Optional[ButtonContent] = DEFAULT_CANCEL,
        cancel_style: ButtonStyleType = DEFAULT_CANCEL_STYLE,
    ) -> None:
        button_confirm = None  # type: Optional[Button]
        button_cancel = None  # type: Optional[Button]

        if confirm is not None:
            button_confirm = Button(True, confirm, confirm_style)
            button_confirm.on_click = self.on_confirm  # type: ignore

        if cancel is not None:
            button_cancel = Button(False, cancel, cancel_style)
            button_cancel.on_click = self.on_cancel  # type: ignore

        super().__init__(content, button_confirm, button_cancel)
