from typing import TYPE_CHECKING

import storage.cache as storage_cache
import trezorui2
from trezor import ui

from . import RustLayout

if TYPE_CHECKING:
    from typing import Any, Tuple

    from trezor import loop


class HomescreenBase(RustLayout):
    RENDER_INDICATOR: object | None = None

    def __init__(self, layout: Any) -> None:
        super().__init__(layout=layout)

    def _paint(self) -> None:
        self.layout.paint()
        ui.refresh()

    def _first_paint(self) -> None:
        if storage_cache.homescreen_shown is not self.RENDER_INDICATOR:
            super()._first_paint()
            storage_cache.homescreen_shown = self.RENDER_INDICATOR
        else:
            self._paint()

    if __debug__:
        # In __debug__ mode, ignore {confirm,swipe,input}_signal.
        def create_tasks(self) -> tuple[loop.AwaitableTask, ...]:
            return (
                self.handle_timers(),
                self.handle_input_and_rendering(),
                self.handle_click_signal(),  # so we can receive debug events
            )


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
            notification = notification.rstrip("!")
            if "COINJOIN" in notification.upper():
                level = 3
            elif "EXPERIMENTAL" in notification.upper():
                level = 2
            elif notification_is_error:
                level = 0

        skip = storage_cache.homescreen_shown is self.RENDER_INDICATOR
        super().__init__(
            layout=trezorui2.show_homescreen(
                label=label,
                notification=notification,
                notification_level=level,
                hold=hold_to_lock,
                skip_first_paint=skip,
            ),
        )

    async def usb_checker_task(self) -> None:
        from trezor import io, loop

        usbcheck = loop.wait(io.USB_CHECK)
        while True:
            is_connected = await usbcheck
            self.layout.usb_event(is_connected)
            self.layout.paint()
            ui.refresh()

    def create_tasks(self) -> Tuple[loop.AwaitableTask, ...]:
        return super().create_tasks() + (self.usb_checker_task(),)


class Lockscreen(HomescreenBase):
    RENDER_INDICATOR = storage_cache.LOCKSCREEN_ON
    BACKLIGHT_LEVEL = ui.BACKLIGHT_LOW

    def __init__(
        self,
        label: str | None,
        bootscreen: bool = False,
    ) -> None:
        self.bootscreen = bootscreen
        if bootscreen:
            self.BACKLIGHT_LEVEL = ui.BACKLIGHT_NORMAL

        skip = (
            not bootscreen and storage_cache.homescreen_shown is self.RENDER_INDICATOR
        )
        super().__init__(
            layout=trezorui2.show_lockscreen(
                label=label,
                bootscreen=bootscreen,
                skip_first_paint=skip,
            ),
        )

    async def __iter__(self) -> Any:
        result = await super().__iter__()
        if self.bootscreen:
            self.request_complete_repaint()
        return result


class Busyscreen(HomescreenBase):
    RENDER_INDICATOR = storage_cache.BUSYSCREEN_ON

    def __init__(self, delay_ms: int) -> None:
        skip = storage_cache.homescreen_shown is self.RENDER_INDICATOR
        super().__init__(
            layout=trezorui2.show_progress_coinjoin(
                title="Waiting for others",
                indeterminate=True,
                time_ms=delay_ms,
                skip_first_paint=skip,
            )
        )

    async def __iter__(self) -> Any:
        from apps.base import set_homescreen

        # Handle timeout.
        result = await super().__iter__()
        assert result == trezorui2.CANCELLED
        storage_cache.delete(storage_cache.APP_COMMON_BUSY_DEADLINE_MS)
        set_homescreen()
        return result
