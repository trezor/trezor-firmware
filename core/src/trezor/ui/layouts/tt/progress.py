from typing import TYPE_CHECKING

import trezorui2
from trezor import TR, ui

if TYPE_CHECKING:
    from typing import Any

    from ..common import ProgressLayout


class RustProgress:
    def __init__(
        self,
        layout: Any,
    ):
        self.layout = layout
        ui.backlight_fade(ui.style.BACKLIGHT_DIM)
        self.layout.attach_timer_fn(self.set_timer)
        self.layout.paint()
        ui.backlight_fade(ui.style.BACKLIGHT_NORMAL)

    def set_timer(self, token: int, deadline: int) -> None:
        raise RuntimeError  # progress layouts should not set timers

    def report(self, value: int, description: str | None = None):
        msg = self.layout.progress_event(value, description or "")
        assert msg is None
        self.layout.paint()
        ui.refresh()


def progress(
    message: str | None = None,
    description: str | None = None,
    indeterminate: bool = False,
) -> ProgressLayout:
    message = message or TR.progress__please_wait  # def_arg
    return RustProgress(
        layout=trezorui2.show_progress(
            title=message.upper(),
            indeterminate=indeterminate,
            description=description or "",
        )
    )


def bitcoin_progress(message: str) -> ProgressLayout:
    return progress(message)


def coinjoin_progress(message: str) -> ProgressLayout:
    return RustProgress(
        layout=trezorui2.show_progress_coinjoin(title=message, indeterminate=False)
    )


def pin_progress(message: str, description: str) -> ProgressLayout:
    return progress(message, description=description)


def monero_keyimage_sync_progress() -> ProgressLayout:
    return progress("", TR.progress__syncing)


def monero_live_refresh_progress() -> ProgressLayout:
    return progress("", TR.progress__refreshing, indeterminate=True)


def monero_transaction_progress_inner() -> ProgressLayout:
    return progress("", TR.progress__signing_transaction)
