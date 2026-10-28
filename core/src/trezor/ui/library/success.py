"""The closing screen: the flow has finished, or the value matched.

Awaited, never spawned. A spawned layout starts with
`workflow.close_others()`, which shuts down the task serving the app before it
answers; awaiting keeps that task running.

`trezorui_api.show_success` is called rather than a model's `show_success`,
because this screen is the same on every model: the check mark, the title, the
description and the timeout. Only `name` differs between callers — `done` names the
step, so a host sees the ButtonRequest, while a verified address has already sent
its own and asks for none.
"""

import trezorui_api
from trezor import TR, utils
from trezor.enums import ButtonRequestType
from trezor.ui.layouts.common import interact

# how long the message stays up before the screen goes away
_TIMEOUT_MS = 3200


def _timeout() -> int:
    """How long to leave the screen up, if at all.

    A model's timeout layout dismisses itself at once when animations are off, so
    the screen would be gone before its ButtonRequest left. Then the screen waits
    for a tap instead, which is what a host driving the device does anyway.
    """
    return 0 if utils.DISABLE_ANIMATION else _TIMEOUT_MS


async def show(name: str | None, text: str) -> None:
    """Say `text`, send a ButtonRequest called `name` if there is one, and go."""
    with trezorui_api.show_success(
        title=TR.words__title_done,
        button=TR.instructions__continue_in_app,
        description=text,
        allow_cancel=False,
        time_ms=_timeout(),
    ) as layout:
        await interact(layout, name, ButtonRequestType.Success)
