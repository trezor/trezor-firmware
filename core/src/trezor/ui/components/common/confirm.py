from trezor import loop, ui, wire
from trezor.ui import CANCELLED, CONFIRMED, GO_BACK, INFO, SHOW_PAGINATED  # noqa: F401

if False:
    from typing import Callable, Any, Awaitable, TypeVar

    T = TypeVar("T")


def is_confirmed(x: Any) -> bool:
    return x is CONFIRMED


async def raise_if_cancelled(a: Awaitable[T], exc: Any = wire.ActionCancelled) -> T:
    result = await a
    if result is CANCELLED:
        raise exc
    return result


async def is_confirmed_info(
    ctx: wire.GenericContext,
    dialog: ui.Layout,
    info_func: Callable,
) -> bool:
    while True:
        result = await ctx.wait(dialog)

        if result is INFO:
            await info_func(ctx)
        else:
            return is_confirmed(result)


class ConfirmBase(ui.Layout):
    def __init__(
        self,
        content: ui.Component,
        confirm: ui.Component | None = None,
        cancel: ui.Component | None = None,
    ) -> None:
        super().__init__()
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


class Pageable:
    def __init__(self) -> None:
        self._page = 0

    def page(self) -> int:
        return self._page

    def page_count(self) -> int:
        raise NotImplementedError

    def is_first(self) -> bool:
        return self._page == 0

    def is_last(self) -> bool:
        return self._page == self.page_count() - 1

    def next(self) -> None:
        self._page = min(self._page + 1, self.page_count() - 1)

    def prev(self) -> None:
        self._page = max(self._page - 1, 0)
