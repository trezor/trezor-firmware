import utime
from micropython import const
from typing import TYPE_CHECKING

import storage.cache as storage_cache
import trezorui_api
from storage.cache_common import APP_COMMON_BUSY_DEADLINE_MS
from trezor import TR, ui, utils

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from typing import Any, ParamSpec, TypeVar

    from trezor import loop

    P = ParamSpec("P")
    R = TypeVar("R")

# When a host request finds the device locked, the host is about to show its own screen
# after the PIN (e.g. the first confirm screen of a Send), but first sends more requests
# (open a session, public keys) and fetches data: measured 2.2-2.5 s on desktop Suite
# over USB, 5.3 s on the first Send after a restart. The homescreen would redraw itself
# in the pauses between these requests and flash before the host's screen. So it keeps
# the PIN loader up while the host keeps going: up to this long after each of its
# requests. The longest pause measured during a Send was 275 ms; when Suite connects to
# a locked device, one pause is longer than 1 s. If a host still makes the homescreen
# flash after an unlock, measure the pauses between its requests and raise this...
_AFTER_HOST_STEP_MS = const(2000)
# ...but no longer than this after the unlock in total, so that a host which keeps
# sending requests without ever showing a screen (e.g. loading accounts) can't keep
# the homescreen away indefinitely.
_AFTER_HOST_UNLOCK_MAX_MS = const(6000)


async def _wait_before_redraw() -> None:
    """Delay the homescreen's redraw while the host that just unlocked the device is
    still on its way to its own screen. If that screen comes up meanwhile, the
    homescreen is closed before it is drawn."""
    from trezor import loop

    # Re-check after each sleep: a request that doesn't restart the main loop (e.g.
    # `GetFeatures`) can end while the homescreen sleeps, which moves the deadline.
    while True:
        unlocked = storage_cache.host_unlocked_ms
        if unlocked is None:
            return
        now = utime.ticks_ms()
        if utime.ticks_diff(now, unlocked) >= _AFTER_HOST_UNLOCK_MAX_MS:
            return

        ended = storage_cache.workflow_ended_ms
        if ended is None or utime.ticks_diff(ended, unlocked) < 0:
            ended = unlocked
        due = utime.ticks_add(ended, _AFTER_HOST_STEP_MS)
        latest = utime.ticks_add(unlocked, _AFTER_HOST_UNLOCK_MAX_MS)
        if utime.ticks_diff(due, latest) > 0:
            due = latest

        remaining = utime.ticks_diff(due, now)
        if remaining <= 0:
            return
        await loop.sleep(remaining)


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


class UsbAwareLayout(ui.Layout):
    """Layout that listens for USB connect/disconnect events."""

    async def usb_checker_task(self) -> None:
        from trezor import io, loop

        usbcheck = loop.wait(io.USB_EVENT)
        while True:
            event = await usbcheck
            self._event(self.layout.usb_event, event)

    def create_tasks(self) -> Iterator[loop.Task[None]]:
        yield from super().create_tasks()
        yield self.usb_checker_task()


class HomescreenLayout(UsbAwareLayout):
    def __init__(
        self,
        layout: trezorui_api.LayoutObj[trezorui_api.UiResult],
        render_indicator: object,
    ) -> None:
        super().__init__(layout)
        self.render_indicator = render_indicator

    def _paint(self) -> None:
        self.layout.paint()

    def _first_paint(self) -> None:
        if not self.should_resume:
            super()._first_paint()
            storage_cache.homescreen_shown = self.render_indicator
        else:
            self._paint()


class HomescreenBase:
    RENDER_INDICATOR: object | None = None

    def __init__(self, ctx: trezorui_api.LayoutContext[trezorui_api.UiResult]) -> None:
        self.ctx = ctx

    @classmethod
    def _should_resume(cls) -> bool:
        return storage_cache.homescreen_shown is cls.RENDER_INDICATOR

    def __enter__(self) -> HomescreenLayout:
        layout = HomescreenLayout(self.ctx.__enter__(), self.RENDER_INDICATOR)
        layout.should_resume = self._should_resume()
        return layout

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Drop internal Rust root component."""
        self.ctx.__exit__(exc_type, exc_val, exc_tb)


async def run_homescreen(
    label: str | None,
    notification: tuple[str, int, bool] | None,
    lockable: bool,
) -> ui.UiResult:
    class Homescreen(HomescreenBase):
        RENDER_INDICATOR = storage_cache.HOMESCREEN_ON

    if not Homescreen._should_resume():
        await _wait_before_redraw()

    with Homescreen(
        _retry_with_gc(
            trezorui_api.show_homescreen,
            label=label or utils.MODEL_FULL_NAME,
            notification=notification,
            lockable=lockable,
            skip_first_paint=Homescreen._should_resume(),
        )
    ) as layout:
        return await layout.get_result()


async def run_lockscreen(
    label: str | None,
    bootscreen: bool = False,
    coinjoin_authorized: bool = False,
) -> ui.UiResult:
    class Lockscreen(HomescreenBase):
        RENDER_INDICATOR = storage_cache.LOCKSCREEN_ON

    skip = not bootscreen and Lockscreen._should_resume()
    with Lockscreen(
        _retry_with_gc(
            trezorui_api.show_lockscreen,
            label=label,
            bootscreen=bootscreen,
            skip_first_paint=skip,
            coinjoin_authorized=coinjoin_authorized,
        )
    ) as layout:
        layout.backlight_level = ui.BacklightLevels.LOW
        if bootscreen:
            layout.backlight_level = ui.BacklightLevels.NORMAL
        layout.should_resume = skip

        result = await layout.get_result()
        if bootscreen:
            # todo: should this be repaint()?
            layout.request_complete_repaint()
        return result


async def run_busyscreen(delay_ms: int) -> ui.UiResult:
    class Busyscreen(HomescreenBase):
        RENDER_INDICATOR = storage_cache.BUSYSCREEN_ON

    with Busyscreen(
        _retry_with_gc(
            trezorui_api.show_progress_coinjoin,
            title=TR.coinjoin__waiting_for_others,
            indeterminate=True,
            time_ms=delay_ms,
            skip_first_paint=Busyscreen._should_resume(),
        )
    ) as layout:
        from trezor.wire import context

        from apps.common.lock_manager import set_homescreen

        result = await layout.get_result()

        # Handle timeout.
        assert result == trezorui_api.CANCELLED
        context.cache_delete(APP_COMMON_BUSY_DEADLINE_MS)
        set_homescreen()
        return result
