from trezor import loop, ui

if __debug__:
    from apps.debug import confirm_signal

if False:
    from typing import List, Tuple, Optional

CONFIRMED = object()
CANCELLED = object()
INFO = object()


class ConfirmBase(ui.Layout):
    def __init__(
        self,
        content: ui.Component,
        confirm: Optional[ui.Component] = None,
        cancel: Optional[ui.Component] = None,
    ) -> None:
        self.content = content
        self.confirm = confirm
        self.cancel = cancel

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
