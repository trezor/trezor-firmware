from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.ui.layouts import StrPropertyType

# Every phase-1 screen carries this. The value on screen came from the host and nothing
# on the device authenticates it -- no keyed path, no proof, no root, no encryption --
# so the host can return any value for any request and the device cannot tell.
#
# FIXME(ward): do NOT remove this warning until the proof path lands and the device can
# actually reject a wrong answer.
WARNING_UNVERIFIED: "StrPropertyType" = (
    "Warning",
    "Not verified by this device.",
    False,
)

# FIXME(ward): all WARD screen strings are hardcoded English. They need to move into the
# translation blobs (TR.*) before this is shippable; kept literal while the wire shape
# and the screens are still moving.


def display_bytes(value: bytes) -> str:
    """Best-effort rendering of an arbitrary byte string for a trusted screen:
    UTF-8 when it decodes cleanly, otherwise hex."""
    try:
        return value.decode()
    except UnicodeError:
        from ubinascii import hexlify

        return hexlify(value).decode()


def require_key(app_id: str | None, identifier: bytes | None) -> "tuple[str, bytes]":
    """Validate the (app_id, identifier) pair every WARD request carries.

    The wire fields are `optional` on purpose -- a proto2 `required` field a caller
    forgets to set is an encode-time failure in every binding -- so the check lives
    here instead, and runs before anything is pulled or shown.
    """
    from trezor.wire import DataError

    if not app_id or not identifier:
        raise DataError("app_id and identifier are required")
    return app_id, identifier


async def pull_entry(app_id: str, identifier: bytes) -> bytes | None:
    """PULL the host's current value for (app_id, identifier).

    This is the one mechanism the whole subsystem is built on: the device holds nothing,
    so it asks the host mid-workflow and the host answers while its own call is still in
    flight. Reads show what comes back; writes use it to learn the value they are about
    to replace or remove.

    Returns None when the host reports no such entry, which stays distinct from b"" --
    an entry that exists and whose value happens to be empty.
    """
    from trezor.messages import WARDEntryAck, WARDEntryRequest
    from trezor.wire import context

    # Mirrors apps/webauthn/list_resident_credentials.py, which uses the same primitive
    # to ask the host for data mid-workflow.
    ack = await context.call(
        WARDEntryRequest(app_id=app_id, identifier=identifier),
        expected_type=WARDEntryAck,
    )
    return ack.value
