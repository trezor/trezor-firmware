from typing import *
from buffer_types import *


# rust/src/trezorhal/nfc/micropython.rs
def set_connected(uid: AnyBytes | None) -> None:
    """Place a card with the given UID in the field, or remove it if `uid`
    is None. Removing the card fails the exchange in progress. Stopping
    discovery removes the card too."""


# rust/src/trezorhal/nfc/micropython.rs
def get_command() -> tuple[bytes, bool] | None:
    """Take the frame waiting to be sent to the card, together with a flag
    that is True for the PSK share and False for a command APDU. Returns
    None if no exchange has been started. Raises EOFError if the card is
    not in the field."""


# rust/src/trezorhal/nfc/micropython.rs
def set_response(response: AnyBytes | int) -> None:
    """Complete the exchange with the card's response, or fail it with the
    given error code. Raises EOFError if the card is not in the field."""
