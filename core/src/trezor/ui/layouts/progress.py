from typing import TYPE_CHECKING

import trezorui2
from trezor import TR, config, ui, utils

if TYPE_CHECKING:
    from typing import Any

    from .common import ProgressLayout


def _storage_message_to_str(message: config.StorageMessage | None) -> str | None:
    from trezor import TR

    if message is None:
        return None

    if message == config.StorageMessage.NO_MSG:
        return ""
    if message == config.StorageMessage.VERIFYING_PIN_MSG:
        return TR.storage_msg__verifying_pin
    if message == config.StorageMessage.PROCESSING_MSG:
        return TR.storage_msg__processing
    if message == config.StorageMessage.STARTING_MSG:
        return TR.storage_msg__starting
    if message == config.StorageMessage.WRONG_PIN_MSG:
        return TR.storage_msg__wrong_pin
    raise RuntimeError  # unknown message


class RustProgress:
    def __init__(
        self,
        layout: Any,
    ):
        self.layout = layout
        ui.backlight_fade(ui.BacklightLevels.DIM)
        self.layout.attach_timer_fn(self.set_timer, None)
        if self.layout.paint():
            ui.refresh()
        ui.backlight_fade(ui.BacklightLevels.NORMAL)

    def set_timer(self, token: int, duration_ms: int) -> None:
        raise RuntimeError  # progress layouts should not set timers

    def report(self, value: int, description: str | None = None):
        msg = self.layout.progress_event(value, description or "")
        assert msg is None
        if self.layout.paint():
            ui.refresh()


def progress(
    description: str | None = None,
    title: str | None = None,
    indeterminate: bool = False,
) -> ProgressLayout:
    if description is None:
        description = TR.progress__please_wait  # def_arg

    return RustProgress(
        layout=trezorui2.show_progress(
            description=description,
            title=title,
            indeterminate=indeterminate,
        )
    )


def bitcoin_progress(message: str) -> ProgressLayout:
    return progress(message)


def coinjoin_progress(message: str) -> ProgressLayout:
    return RustProgress(
        layout=trezorui2.show_progress_coinjoin(title=message, indeterminate=False)
    )


def pin_progress(title: config.StorageMessage, description: str) -> ProgressLayout:
    return progress(description=description, title=_storage_message_to_str(title))


if not utils.BITCOIN_ONLY:

    def monero_keyimage_sync_progress() -> ProgressLayout:
        return progress(TR.progress__syncing)

    def monero_live_refresh_progress() -> ProgressLayout:
        return progress(TR.progress__refreshing, indeterminate=True)

    def monero_transaction_progress_inner() -> ProgressLayout:
        return progress(TR.progress__signing_transaction)
