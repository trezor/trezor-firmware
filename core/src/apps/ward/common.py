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
    here instead, and runs before anything is derived, pulled or shown.

    Also refuses an uninitialised device: deriving the keyed path needs a seed.
    """
    from trezor.wire import DataError

    from apps.common.seed import raise_if_not_initialized

    raise_if_not_initialized()

    if not app_id or not identifier:
        raise DataError("app_id and identifier are required")
    return app_id, identifier


async def pull_entry(entry_key: bytes, key_type: str) -> bytes | None:
    """PULL the host's current value for an already-derived keyed path.

    This is the one mechanism the whole subsystem is built on: the device holds nothing,
    so it asks the host mid-workflow and the host answers while its own call is still in
    flight. Reads show what comes back; writes use it to learn the value they are about
    to replace or remove.

    The request names ONLY the opaque path -- see `keys.entry_key_for`. Callers must
    derive it themselves and must never pass through a host-supplied value.

    What comes back is a two-part LEAF, which this decodes down to the value the screens
    care about. Returns None when the host holds no such entry OR the leaf it returned
    is a tombstone; both mean "nothing here". That stays distinct from b"" -- an entry
    that exists and whose value happens to be empty.

    The identity part is deliberately NOT returned. Nothing reads it yet: the device
    already knows the identifier and app_id (it derived the path from them), so the
    identity part is write-only until there is a consumer that does not -- host-blind
    reconstruction, or enumerating entries without knowing their identifiers.
    """
    from trezor.messages import WARDEntryAck, WARDEntryRequest
    from trezor.wire import context

    from .leaf import decode_content, read_leaf_content

    # Mirrors apps/webauthn/list_resident_credentials.py, which uses the same primitive
    # to ask the host for data mid-workflow.
    ack = await context.call(
        WARDEntryRequest(entry_key=entry_key),
        expected_type=WARDEntryAck,
    )

    decoded = decode_content(entry_key, key_type, read_leaf_content(ack.content))
    if decoded is None:
        return None
    _c_leaf, value = decoded
    return value
