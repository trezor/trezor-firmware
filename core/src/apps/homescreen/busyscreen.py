from typing import TYPE_CHECKING

import storage.cache as storage_cache

from . import HomescreenBase

if TYPE_CHECKING:
    from trezor import loop


async def busyscreen() -> None:
    await Busyscreen()


class Busyscreen(HomescreenBase):
    RENDER_INDICATOR = storage_cache.BUSYSCREEN_ON

    def create_tasks(self) -> tuple[loop.AwaitableTask, ...]:
        return self.handle_rendering(), self.handle_input(), self.handle_expiry()

    def handle_expiry(self) -> loop.Task:  # type: ignore [awaitable-is-generator]
        from apps.base import busy_expiry_ms, set_homescreen
        from trezor import ui, loop

        yield loop.sleep(busy_expiry_ms())
        storage_cache.delete(storage_cache.APP_COMMON_BUSY_DEADLINE_MS)
        set_homescreen()
        raise ui.Result(None)

    def do_render(self) -> None:
        from trezor.ui.layouts import show_coinjoin

        show_coinjoin()
