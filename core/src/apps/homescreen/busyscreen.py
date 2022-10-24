import storage.cache
from trezor import loop, ui
from trezor.ui.layouts import show_coinjoin

from apps.base import busy_expiry_ms, set_homescreen

from . import HomescreenBase


async def busyscreen() -> None:
    await Busyscreen()


class Busyscreen(HomescreenBase):
    RENDER_INDICATOR = storage.cache.BUSYSCREEN_ON

    def create_tasks(self) -> tuple[loop.AwaitableTask, ...]:
        return self.handle_rendering(), self.handle_input(), self.handle_expiry()

    def handle_expiry(self) -> loop.Task:  # type: ignore [awaitable-is-generator]
        yield loop.sleep(busy_expiry_ms())
        storage.cache.delete(storage.cache.APP_COMMON_BUSY_DEADLINE_MS)
        set_homescreen()
        raise ui.Result(None)

    def do_render(self) -> None:
        show_coinjoin()
