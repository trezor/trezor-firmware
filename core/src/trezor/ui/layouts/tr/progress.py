from typing import TYPE_CHECKING

from trezor import ui

import trezorui2

if TYPE_CHECKING:
    from typing import Any

    from ..common import ProgressLayout


class RustProgress:
    def __init__(
        self,
        layout: Any,
    ):
        self.layout = layout
        ui.display.clear()
        self.layout.attach_timer_fn(self.set_timer)
        self.layout.paint()

    def set_timer(self, token: int, deadline: int) -> None:
        raise RuntimeError  # progress layouts should not set timers

    def report(self, value: int, description: str | None = None):
        msg = self.layout.progress_event(value, description or "")
        assert msg is None
        self.layout.paint()
        ui.refresh()


def progress(
    message: str = "PLEASE WAIT",
    description: str | None = None,
    indeterminate: bool = False,
) -> ProgressLayout:
    return RustProgress(
        layout=trezorui2.show_progress(
            title=message.upper(),
            indeterminate=indeterminate,
            description=description or "",
        )
    )


def bitcoin_progress(description: str) -> ProgressLayout:
    return progress("", description)


def coinjoin_progress(message: str) -> ProgressLayout:
    # TODO: create show_progress_coinjoin for TR
    return progress("Coinjoin", message)
    # return RustProgress(
    #     layout=trezorui2.show_progress_coinjoin(title=message, indeterminate=False)
    # )


def pin_progress(message: str, description: str) -> ProgressLayout:
    return progress(message, description)


def monero_keyimage_sync_progress() -> ProgressLayout:
    return progress("", "Syncing...")


def monero_live_refresh_progress() -> ProgressLayout:
    return progress("", "Refreshing...", indeterminate=True)


def monero_transaction_progress_inner() -> ProgressLayout:
    return progress("", "Signing transaction...")
