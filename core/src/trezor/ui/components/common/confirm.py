from typing import TYPE_CHECKING

from trezor import ui, wire

import trezorui2

if TYPE_CHECKING:
    from typing import Callable, Any, Awaitable, TypeVar

    T = TypeVar("T")

CONFIRMED = trezorui2.CONFIRMED
CANCELLED = trezorui2.CANCELLED
INFO = trezorui2.INFO


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
