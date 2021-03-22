from trezor import loop, ui, wire

if False:
    from typing import Any, Awaitable

CONFIRMED = object()
CANCELLED = object()
INFO = object()


def is_confirmed(x: Any) -> bool:
    return x is CONFIRMED


async def raise_if_cancelled(a: Awaitable, exc: Any = wire.ActionCancelled) -> None:
    result = await a
    if result is CANCELLED:
        raise exc


class ConfirmBase(ui.Layout):
    def __init__(
        self,
        content: ui.Component,
        confirm: ui.Component | None = None,
        cancel: ui.Component | None = None,
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

        def read_content(self) -> list[str]:
            return self.content.read_content()

        def create_tasks(self) -> tuple[loop.Task, ...]:
            from apps.debug import confirm_signal

            return super().create_tasks() + (confirm_signal(),)
