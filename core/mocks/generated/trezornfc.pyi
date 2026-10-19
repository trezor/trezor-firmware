from typing import *
from buffer_types import *


# rust/src/trezorhal/nfc/micropython.rs
def start_discovery() -> None:
    """Activate electromagnetic field and start searching for an NFC tag. Caller should poll
    for the `NFC_CONNECTED` event and then call `connect()`."""


# rust/src/trezorhal/nfc/micropython.rs
def stop_discovery() -> None:
    """Disables electromagnetic field and disconnects any active NFC tag."""


# rust/src/trezorhal/nfc/micropython.rs
def connect() -> TagConnection:
    """Return connection handle after `NFC_CONNECTED` occurs. The next step is to call its
    `setup()` method."""


# rust/src/trezorhal/nfc/micropython.rs
class TagConnection:
    """Represents active communications session with powered-on NFC tag."""
    def uid(self) -> bytes:
        """Returns tag ID."""
    def setup(self, static_private_key: bytes | None, static_public_key: bytes | None, pin: str | None, verify_fn: Callable[[bytes, bytes], bool]) -> bool:
        """Select applet, open secure channel (optional) and authenticate with PIN (optional).
        Returns True if complete and ready for issuing commands. Otherwise the caller needs
        to poll for `NFC_TRANSCEIVE_DONE` and call the function again, repeating until it
        returns True or raises an exception. Session is invalid after receiving `NFC_DISCONNECTED`.
        Callback `verify_fn` is used to check remote static public key and certificate."""
    def send_command(self, ins: int, data: AnyBytes | None) -> None:
        """Schedule asynchronous sending of ISO-DEP command. Caller needs to poll for the
        `NFC_TRANSCEIVE_DONE` event, then call `recv_response` to obtain the response or error."""
    def recv_response(self) -> bytes | None:
        """Return tag's response to previously called `send_command`."""


# rust/src/trezorhal/nfc/micropython.rs
class NfcError(RuntimeError):
    pass


# rust/src/trezorhal/nfc/micropython.rs
class NfcCommandFailed(NfcError):
    """`arg[0]` is 16-bit status code, `arg[1]` is its text representation or None"""
SET_PIN: int
WIPE: int
READ_PIN_COUNTER: int
READ_SUCCESS_LOG: int
READ_FAILURE_LOGS: int
READ_SEED_METADATA: int
WRITE_SEED_METADATA: int
READ_SEED: int
WRITE_SEED: int
GET_OS_VERSION: int
GET_UID: int
MEASURE_CPU_FREQUENCY: int
HARDEN_MEMORY: int
INTEGRITY_CHECK: int
PIN_UNLOCKED: int
