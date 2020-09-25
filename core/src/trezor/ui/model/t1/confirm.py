from trezor import loop, ui

from ..common import CANCELLED, CONFIRMED
from .button import Button, ButtonBlack, ButtonWhite

if __debug__:
    from apps.debug import confirm_signal


if False:
    from typing import Optional, List, Tuple
    from .button import ButtonContent, ButtonStyleType


class Confirm(ui.Layout):
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
        self.content = content

        if confirm is not None:
            self.confirm = Button(
                True, confirm, confirm_style
            )  # type: Optional[Button]
            self.confirm.on_click = self.on_confirm  # type: ignore
        else:
            self.confirm = None

        if cancel is not None:
            self.cancel = Button(False, cancel, cancel_style)  # type: Optional[Button]
            self.cancel.on_click = self.on_cancel  # type: ignore
        else:
            self.cancel = None

    def dispatch(self, event: int, x: int, y: int) -> None:
        super().dispatch(event, x, y)
        self.content.dispatch(event, x, y)
        if self.confirm is not None:
            self.confirm.dispatch(event, x, y)
        if self.cancel is not None:
            self.cancel.dispatch(event, x, y)

    def on_confirm(self) -> None:
        raise ui.Result(CONFIRMED)

    def on_cancel(self) -> None:
        raise ui.Result(CANCELLED)

    if __debug__:

        def read_content(self) -> List[str]:
            return self.content.read_content()

        def create_tasks(self) -> Tuple[loop.Task, ...]:
            return super().create_tasks() + (confirm_signal(),)
