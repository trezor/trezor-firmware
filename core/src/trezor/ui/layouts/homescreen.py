from typing import TYPE_CHECKING

import storage.cache as storage_cache
import trezorui2
from trezor import TR, ui

if TYPE_CHECKING:
    from typing import Any, Iterator

    from trezor import loop


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
            layout=trezorui2.show_homescreen(
                label=label,
                notification=notification,
                notification_level=level,
                hold=hold_to_lock,
                skip_first_paint=self._should_resume(),
            )
        )

    async def usb_checker_task(self) -> None:
        from trezor import io, loop

        usbcheck = loop.wait(io.USB_CHECK)
        while True:
            is_connected = await usbcheck
            self._event(self.layout.usb_event, is_connected)

    def create_tasks(self) -> Iterator[loop.Task]:
        yield from super().create_tasks()
        yield self.usb_checker_task()


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
            layout=trezorui2.show_lockscreen(
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
            layout=trezorui2.show_progress_coinjoin(
                title=TR.coinjoin__waiting_for_others,
                indeterminate=True,
                time_ms=delay_ms,
                skip_first_paint=self._should_resume(),
            )
        )

    async def get_result(self) -> Any:
        from apps.base import set_homescreen

        # Handle timeout.
        result = await super().get_result()
        assert result == trezorui2.CANCELLED
        storage_cache.delete(storage_cache.APP_COMMON_BUSY_DEADLINE_MS)
        set_homescreen()
        return result
