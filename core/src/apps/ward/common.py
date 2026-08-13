from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.ui.layouts import StrPropertyType

# Every screen carries this. Sealing the leaf narrowed what needs warning about, but did
# not remove it:
#
#   the host CANNOT forge a value, or move a leaf from one path to another -- the AEAD tag
#   fails, so anything that reaches a screen really was sealed by this device for this
#   path;
#   the host CAN return an OLDER sealed leaf for that path, or claim it holds none at all.
#
# So the value is authentic but its freshness is unproven, and that is what the wording
# has to say. It would be actively worse to soften this to "encrypted": a decrypted value
# looks authoritative on screen, so a vaguer warning next to a more trustworthy value
# misleads more than the blunt version did.
#
# FIXME(ward): do NOT remove this warning until proofs against an attested root land --
# only those detect a stale leaf or a suppressed entry.
WARNING_UNVERIFIED: "StrPropertyType" = (
    "Warning",
    "Not proven current; may be out of date.",
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

    from .keys import derive_k_data
    from .leaf import decode_content, read_leaf_content

    # Mirrors apps/webauthn/list_resident_credentials.py, which uses the same primitive
    # to ask the host for data mid-workflow.
    ack = await context.call(
        WARDEntryRequest(entry_key=entry_key),
        expected_type=WARDEntryAck,
    )

    part = read_leaf_content(ack.content)
    if part is None:
        return None

    # Opening is also the only authenticity check available at this phase: a part the host
    # forged, corrupted, or lifted from another path fails the tag and raises here.
    decoded = decode_content(await derive_k_data(key_type), entry_key, key_type, part)
    if decoded is None:
        return None
    _c_leaf, value = decoded
    return value
