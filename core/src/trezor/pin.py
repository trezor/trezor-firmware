from micropython import const
from typing import TYPE_CHECKING

from . import config

if TYPE_CHECKING:
    from typing import Any

    from trezor.ui import ProgressLayout

_previous_seconds: int | None = None
_previous_remaining: str | None = None
_progress_layout: ProgressLayout | None = None
_started_with_empty_loader = False
keepalive_callback: Any = None

_ignore_loader_messages: bool = False


def ignore_nonpin_loader_messages() -> None:
    global _ignore_loader_messages
    _ignore_loader_messages = True


def allow_all_loader_messages() -> None:
    global _ignore_loader_messages
    _ignore_loader_messages = False


def render_empty_loader(
    message: config.StorageMessage, description: str = "", danger: bool = False
) -> None:
    """Render empty loader to prevent the screen from appearing frozen.

    Args:
        message (config.StorageMessage): The message to display in the loader.
        description (str, optional): Additional description to display. Defaults to an empty string.
        danger (bool, optional): If True, renders the loader in a 'danger' style to indicate a critical operation (e.g. wipe device). Defaults to False.
    """
    from trezor.ui.layouts.progress import pin_progress

    global _progress_layout
    global _started_with_empty_loader

    _progress_layout = pin_progress(message, description, danger)
    _progress_layout.report(0, None)

    _started_with_empty_loader = True


def show_pin_timeout(
    seconds: int, progress: int, message: config.StorageMessage
) -> bool:
    from trezor import TR
    from trezor.ui.layouts.progress import pin_progress

    # Possibility to ignore certain messages - not showing loader for them
    if _ignore_loader_messages and message in (
        config.StorageMessage.PROCESSING_MSG,
        config.StorageMessage.STARTING_MSG,
    ):
        return False

    global _previous_seconds
    global _previous_remaining
    global _progress_layout
    global _started_with_empty_loader

    if callable(keepalive_callback):
        keepalive_callback()

    if progress == 0 or _progress_layout is None:
        _previous_seconds = None

    if seconds != _previous_seconds:
        if seconds == 0:
            remaining = TR.progress__done
        elif seconds == 1:
            remaining = TR.progress__one_second_left
        else:
            # TODO: make this a plural
            remaining = TR.progress__x_seconds_left_template.format(seconds)
        _previous_remaining = remaining
        _previous_seconds = seconds
    else:
        remaining = _previous_remaining

    # create the layout if it doesn't exist yet or should be started again
    if _progress_layout is None or (progress == 0 and not _started_with_empty_loader):
        _progress_layout = pin_progress(message, description=remaining or "")

    # reset the flag - the render_empty_loader() has the effect only in the first call
    # of this function, where we do not want to re-initialize the layout
    # to avoid a screen flicker
    _started_with_empty_loader = False

    # update the progress layout
    _progress_layout.report(progress, remaining)

    # drop the layout when done so trezor.ui doesn't have to remain in memory
    if progress >= 1000:
        _progress_layout = None
        _previous_remaining = None

    return False


# vault_card_state_t, see sec/vault_card.h
_CARD_WAITING = const(0)
_CARD_DONE = const(1)
_CARD_TIMEOUT = const(2)
_CARD_CANCELLED = const(3)
# How long one prompt update listens for touches. The vault checks the card
# in between.
_CARD_TOUCH_MS = const(40)


class _CardPrompt:
    """The card prompt and its Cancel button.

    It runs inside the vault call that waits for the card, while the event loop
    is blocked, so it polls touch events and serves the layout's timers itself.
    """

    def __init__(self) -> None:
        import trezorui_api
        from trezor import ui

        self.context = trezorui_api.show_info(
            title="Tap your card",
            description="Hold your NFC card to the phone.",
            button=("Cancel", True),
        )
        self.layout = self.context.__enter__()
        self.timers: dict[int, int] = {}
        self.cancelled = False
        # Takes the screen over from the running layout, as PIN progress does.
        self.screen = ui.ProgressLayout(self.layout)
        # No transition: nothing would animate it while the event loop waits.
        self._handle(self.layout.attach_timer_fn(self._set_timer, None))
        self.screen.start()

    def _set_timer(self, token: int, duration_ms: int) -> None:
        import utime

        self.timers[token] = utime.ticks_add(utime.ticks_ms(), duration_ms)

    def _handle(self, state: Any) -> None:
        import trezorui_api

        # The only button is Cancel.
        if state is trezorui_api.LayoutState.DONE:
            self.cancelled = True
        self.layout.paint()

    def update(self) -> bool:
        """Serve touches and timers for a moment. Returns True once cancelled."""
        import utime

        from trezor import io

        entry: list[Any] = [0, 0]  # iface, (event, x, y)
        deadline = utime.ticks_add(utime.ticks_ms(), _CARD_TOUCH_MS)
        while not self.cancelled:
            now = utime.ticks_ms()
            left = utime.ticks_diff(deadline, now)
            if left <= 0:
                break
            for token, due in list(self.timers.items()):
                if utime.ticks_diff(due, now) <= 0:
                    del self.timers[token]
                    self._handle(self.layout.timer(token))
            if io.poll((io.TOUCH,), entry, min(left, 10)):
                event, x, y = entry[1]
                self._handle(self.layout.touch_event(event, x, y))
        return self.cancelled

    def close(self) -> None:
        self.screen.stop()
        self.context.__exit__(None, None, None)


_card_prompt: _CardPrompt | None = None


def show_card_prompt(state: int, remaining_ms: int) -> bool:
    """Ask for the NFC card while the vault waits for it, then show the outcome.

    Emulators built with TREZOR_VAULT_CARD=1 keep the seed on a card. The vault
    calls this repeatedly while it waits for a tap, then once with the outcome
    of the operation. Returns True to stop waiting, when the user cancels.
    Experimental, so the texts are not translated.
    """
    import utime

    from trezor.ui.layouts.progress import progress

    global _card_prompt

    if state == _CARD_WAITING:
        if callable(keepalive_callback):
            keepalive_callback()
        if _card_prompt is None:
            _card_prompt = _CardPrompt()
        return _card_prompt.update()

    if _card_prompt is not None:
        _card_prompt.close()
        _card_prompt = None
    if state == _CARD_DONE:
        title, description = "Card read", "Done."
    elif state == _CARD_TIMEOUT:
        title, description = "No card", "No card was tapped in time."
    elif state == _CARD_CANCELLED:
        title, description = "Cancelled", "The card was not read."
    else:
        title = "Card error"
        description = (
            "The card could not be read. Hold it still, and check that it is your card."
        )
    failed = state != _CARD_DONE
    result = progress(description, title=title, danger=failed)
    result.report(1000, description)
    # A success returns at once: the workflow may need the card again right
    # away, while it is still held. A failure ends the workflow, so pause to
    # let the user read why.
    if failed:
        utime.sleep_ms(1500)
    return False
