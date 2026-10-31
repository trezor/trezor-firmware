"""The driver that shows an external app's screens, whatever the model.

An app sends what it wants the person to read and decide; the screens themselves,
their styling and their extras are each model's, and only the decision goes back.
"""

from micropython import const

import trezorui_api
from trezor.wire import ActionCancelled
from trezor.wire.errors import DataError

from . import confirm, success, verify
from .fields import button_request_name

# `TrezorUiResult` discriminants, as `encode_ui_result` takes them.
CONFIRMED = const(0)
CANCELLED = const(1)
SHOW_DETAILS = const(5)

# `TrezorUiEnum` discriminants, as `deserialize_ui_message` decodes them.
_REVIEW = const(0)
_DANGER = const(1)
_DETAILS = const(2)
_VERIFY_ADDRESS = const(3)
_VERIFY_PUBKEY = const(4)
_DONE = const(5)


async def run(request: tuple, app_id: str) -> int:
    """Show the screen `request` asks for and return the person's answer.

    `request` is a decoded UI request; `app_id` is the app's identity, the image
    ID (`testapp.trezor.io`), and it prefixes the name of every ButtonRequest
    sent. A refusal returns `CANCELLED` rather than raising, and a request this
    driver cannot draw raises `DataError`.
    """
    try:
        return await _show(request, app_id)
    except ActionCancelled:
        return CANCELLED


async def _show(request: tuple, app_id: str) -> int:
    """Pick the screen for the request's kind and run it."""
    kind, step, *args = request
    name = button_request_name(app_id, step)

    if kind == _REVIEW:
        return _decision(await confirm.review(name, *args))
    if kind == _DANGER:
        return _decision(await confirm.danger(name, *args))
    if kind == _DETAILS:
        return SHOW_DETAILS if await confirm.details(name, *args) else CONFIRMED
    if kind == _VERIFY_ADDRESS:
        await verify.address(name, *args)
        return CONFIRMED
    if kind == _VERIFY_PUBKEY:
        await verify.pubkey(name, *args)
        return CONFIRMED
    if kind == _DONE:
        (text,) = args
        await success.show(name, text)
        return CONFIRMED

    raise DataError(f"Unknown UI request kind {kind}")


def _decision(result: "trezorui_api.UiResult") -> int:
    """The wire's discriminant for a layout's decision."""
    if result is trezorui_api.CONFIRMED:
        return CONFIRMED
    if result is trezorui_api.CANCELLED:
        return CANCELLED
    raise DataError("Unexpected layout result")
