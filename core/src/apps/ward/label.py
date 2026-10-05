"""WARD read for an ON-DEVICE app: resolve what an identifier is CALLED.

Unlike `get_entry` it never confirms and returns rather than displays. The source is chosen UP
FRONT -- verified pull when online, the device's own store otherwise -- so a hostile backend
cannot pick which one the user sees by answering badly. It is the only caller of
`online_or_offline`, because it has an honest offline answer.

Returns `(label, note)`, never a bare label: `note` says which provenance the label has, ready
for `show_address(warning=...)`. Failures are labelling failures, for the caller to absorb.
"""

# Short and blunt: they land in a `warning` slot next to an address.
NOTE_UNVERIFIED = "Label not proven current."
NOTE_ABSENT = "No label for this address."
NOTE_OFFLINE = "Offline label; not checked with the host."
NOTE_PENDING = "Label not published yet."
NOTE_NO_COPY = "No label kept on this device."
NOTE_CORRUPT = "A label is stored here but cannot be read."

# Which firmware modules may ask. The principal is a constant a module passes about itself,
# never from the wire: capability scoping, not authentication.
_CAPABILITIES = {
    "display_address": ("read",),
}


def _authorize(principal: str, capability: str) -> None:
    from trezor.wire import DataError

    if capability not in _CAPABILITIES.get(principal, ()):
        raise DataError("app not authorized for WARD " + capability)


async def resolve_label(
    principal: str,
    identifier: bytes,
    domain: str | None = None,
    key_type: str | None = None,
) -> "tuple[bytes | None, str]":
    """`(label, note)` for `identifier` in `domain` (default: the principal's own).

    `label` is None whenever nothing can be shown; `note` says why. Raises only if the lookup
    could not be performed.
    """
    from . import offline_store
    from .common import online_or_offline, pull_entry, require_initialized
    from .keys import ENTRY_TYPE_ADDRESS, entry_key_for

    _authorize(principal, "read")
    require_initialized()

    app_id = domain if domain is not None else principal
    if key_type is None:
        key_type = ENTRY_TYPE_ADDRESS

    entry_key = await entry_key_for(app_id, identifier, key_type)

    if await online_or_offline():
        value = await pull_entry(entry_key, key_type)
        # ABSENT is proven (a witness was checked); an EMPTY value is a deliberate blank.
        if value is None:
            return None, NOTE_ABSENT
        return value, NOTE_UNVERIFIED

    status, entry = await offline_store.get(key_type, app_id, identifier)

    if status == offline_store.CORRUPT:
        # Not "no label": something is stored here that this build cannot read.
        return None, NOTE_CORRUPT

    if status == offline_store.MISS or entry is None:
        return None, NOTE_NO_COPY

    if entry.pending:
        return entry.value, NOTE_PENDING

    return entry.value, NOTE_OFFLINE
