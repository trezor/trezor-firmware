from typing import TYPE_CHECKING

import storage.cache as storage_cache
import trezorui_api
from storage.cache_common import APP_COMMON_BUSY_DEADLINE_MS
from trezor import TR, ui, utils

if TYPE_CHECKING:
    from typing import Any, Callable, Iterator, ParamSpec, TypeVar

    from trezor import loop

    P = ParamSpec("P")
    R = TypeVar("R")


def _retry_with_gc(layout: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
    """Retry creating the layout after garbage collection.

    For reasons unknown, a previous homescreen layout may survive an unimport, and still
    exists in the GC arena. At the time a new one is instantiated, the old one still
    holds a lock on the JPEG buffer, and creating a new layout will fail with a
    MemoryError.

    It seems that the previous layout's survival is a glitch, and at a later time it is
    still in memory but not held anymore. We assume that triggering a GC cycle will
    correctly throw it away, and we will be able to create the new layout.

    We only try this once because if it didn't help, the above assumption is wrong, so
    no point in trying again.
    """
    try:
        return layout(*args, **kwargs)
    except MemoryError:
        import gc

        gc.collect()
        return layout(*args, **kwargs)


class HomescreenBase(ui.Layout):
    RENDER_INDICATOR: object | None = None

    def __init__(self, layout: Any) -> None:
        super().__init__(layout=layout)
        self.should_resume = self._should_resume()

    def _should_resume(self) -> bool:
        return storage_cache.homescreen_shown is self.RENDER_INDICATOR

    def _paint(self) -> None:
        if self.layout.paint():
            ui.refresh()

    def _first_paint(self) -> None:
        if not self.should_resume:
            super()._first_paint()
            storage_cache.homescreen_shown = self.RENDER_INDICATOR
        # else:
        #     self._paint()


class Homescreen(HomescreenBase):
    RENDER_INDICATOR = storage_cache.HOMESCREEN_ON

    def __init__(
        self,
        label: str | None,
        notification: str | None,
        notification_is_error: bool,
        hold_to_lock: bool,
    ) -> None:
        level = 1
        if notification is not None:
            notification = notification.rstrip(
                "!"
            )  # TODO handle TS5 that doesn't have it
            if notification == TR.homescreen__title_coinjoin_authorized:
                level = 3
            elif notification == TR.homescreen__title_experimental_mode:
                level = 2
            elif notification_is_error:
                level = 0

        super().__init__(
            layout=_retry_with_gc(
                trezorui_api.show_homescreen,
                label=label,
                notification=notification,
                notification_level=level,
                hold=hold_to_lock,
                skip_first_paint=self._should_resume(),
            )
        )

    async def usb_checker_task(self) -> None:
        from trezor import io, loop

        usbcheck = loop.wait(io.USB_EVENT)
        while True:
            event = await usbcheck
            self._event(self.layout.usb_event, event)

    if utils.USE_BLE:

        async def ble_checker_task(self) -> None:
            from trezor import io, loop

            blecheck = loop.wait(io.BLE_EVENT)
            while True:
                event = await blecheck
                self._event(self.layout.ble_event, *event)

    def create_tasks(self) -> Iterator[loop.Task]:
        yield from super().create_tasks()
        yield self.usb_checker_task()
        if utils.USE_BLE:
            yield self.ble_checker_task()


class Lockscreen(HomescreenBase):
    RENDER_INDICATOR = storage_cache.LOCKSCREEN_ON

    def __init__(
        self,
        label: str | None,
        bootscreen: bool = False,
        coinjoin_authorized: bool = False,
    ) -> None:
        self.bootscreen = bootscreen
        self.backlight_level = ui.BacklightLevels.LOW
        if bootscreen:
            self.backlight_level = ui.BacklightLevels.NORMAL

        skip = (
            not bootscreen and storage_cache.homescreen_shown is self.RENDER_INDICATOR
        )
        super().__init__(
            layout=_retry_with_gc(
                trezorui_api.show_lockscreen,
                label=label,
                bootscreen=bootscreen,
                skip_first_paint=skip,
                coinjoin_authorized=coinjoin_authorized,
            ),
        )
        self.should_resume = skip

    async def get_result(self) -> Any:
        result = await super().get_result()
        if self.bootscreen:
            self.request_complete_repaint()
        return result


class Busyscreen(HomescreenBase):
    RENDER_INDICATOR = storage_cache.BUSYSCREEN_ON

    def __init__(self, delay_ms: int) -> None:
        super().__init__(
            layout=_retry_with_gc(
                trezorui_api.show_progress_coinjoin,
                title=TR.coinjoin__waiting_for_others,
                indeterminate=True,
                time_ms=delay_ms,
                skip_first_paint=self._should_resume(),
            )
        )

    async def get_result(self) -> Any:
        from trezor.wire import context

        from apps.base import set_homescreen

        # Handle timeout.
        result = await super().get_result()
        assert result == trezorui_api.CANCELLED
        context.cache_delete(APP_COMMON_BUSY_DEADLINE_MS)
        set_homescreen()
        return result
