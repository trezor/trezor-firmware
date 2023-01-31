from typing import TYPE_CHECKING

import storage.cache as storage_cache
from trezor import ui

import trezorui2

from . import RustLayout

if TYPE_CHECKING:
    from trezor import loop
    from typing import Any, Tuple


class HomescreenBase(RustLayout):
    RENDER_INDICATOR: object | None = None

    def __init__(self, layout: Any) -> None:
        super().__init__(layout=layout)
        self.is_connected = True

    async def __iter__(self) -> Any:
        # We need to catch the ui.Cancelled exception that kills us, because that means
        # that we will need to draw on screen again after restart.
        try:
            return await super().__iter__()
        except ui.Cancelled:
            storage_cache.homescreen_shown = None
            raise

    def _first_paint(self) -> None:
        from trezor import utils

        if storage_cache.homescreen_shown is not self.RENDER_INDICATOR:
            super()._first_paint()
            storage_cache.homescreen_shown = self.RENDER_INDICATOR

        # - RENDER_INDICATOR is set -> USB warning is not displayed
        # - RENDER_INDICATOR is not set -> initially homescreen does not display warning
        # - usb_checker_task only handles state changes
        # Here we need to handle the case when homescreen is started with USB disconnected.
        if not utils.usb_data_connected():
            msg = self.layout.usb_event(False)
            self._paint()
            if msg is not None:
                raise ui.Result(msg)

    # In __debug__ mode, ignore {confirm,swipe,input}_signal.
    def create_tasks(self) -> tuple[loop.AwaitableTask, ...]:
        return self.handle_timers(), self.handle_input_and_rendering()


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
            if "EXPERIMENTAL" in notification:
                level = 2
            elif notification_is_error:
                level = 0

        skip = storage_cache.homescreen_shown is self.RENDER_INDICATOR
        super().__init__(
            layout=trezorui2.show_homescreen(
                label=label or "My Trezor",
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
            if is_connected != self.is_connected:
                self.is_connected = is_connected
                self.layout.usb_event(is_connected)
                self.layout.paint()
                storage_cache.homescreen_shown = None

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
                label=label or "My Trezor",
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
            layout=trezorui2.show_busyscreen(
                title="PLEASE WAIT",
                description="CoinJoin in progress.\n\nDo not disconnect your Trezor.",
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
