"""WARD read for an ON-DEVICE app: resolve what an identifier is CALLED.

WHY THIS IS NOT `get_entry`. Both read one entry, but they answer to different people and
so cannot share an answer. `get_entry` serves the HOST, which asked for a specific entry
and is owed a screen about that entry -- the value, its provenance, a confirmation. This
serves FIRMWARE, which is in the middle of showing something else and wants one more line
on that screen. A label lookup therefore never confirms, never fails the surrounding
workflow, and returns rather than displays.

THE SAME TWO SOURCES, CHOSEN THE SAME WAY. Online (this session has adopted a WM-attested
head) means pull from the host and check the answer against the trusted root; offline means
this device's own store. The choice is made UP FRONT on `round.is_online()`, exactly as in
`get_entry`, and for the same reason: a device that pulled first and fell back to its local
copy on failure would let a hostile host choose which of the two the user sees, simply by
answering badly.

PROVENANCE TRAVELS WITH THE LABEL. The caller gets `(label, note)`, never a bare label,
because the four ways a label can arrive are not interchangeable on a screen a user checks
a recipient against:

  a value pulled and checked against the root this session trusts,
  a local copy authenticated at some earlier counter,
  a change the user made that no host has taken yet,
  nothing at all.

`note` is the sentence that says which, ready to hand to `show_address(warning=...)`. A
caller that wanted only the label would silently present the last three as the first, and
that is the confusion this subsystem exists to prevent -- so there is no such entry point.

FAILURE IS THE CALLER'S TO ABSORB, not to propagate. Anything that goes wrong here is a
LABELLING failure: a host that does not speak WARD, an ack that does not verify, an
uninitialised device. None of them says anything about the address the caller is about to
show, so this raises for the caller to catch and note, and a caller that aborts its own
workflow over it has misread what it asked for.
"""

# The provenance sentences. Short, because they land in a `warning` slot next to an address
# on a small screen, and blunt, because a hedged one reads as reassurance.
NOTE_UNVERIFIED = "Label not proven current."
NOTE_ABSENT = "No label for this address."
NOTE_OFFLINE = "Offline label; not checked with the host."
NOTE_STALE = "Offline label; it has changed since."
NOTE_PENDING = "Label not published yet."
NOTE_NO_COPY = "No label kept on this device."
NOTE_CORRUPT = "A label is stored here but cannot be read."

# WHICH FIRMWARE MODULES MAY ASK. The principal is a constant a firmware module passes about
# ITSELF -- it never arrives from the wire -- so this is capability scoping, not
# authentication: it bounds which on-device apps can turn WARD into a label lookup, and it is
# the list to extend when Bitcoin's or Ethereum's get_address adopts this.
#
# Distinct from the DOMAIN being read, which for `display_address` DOES come from the wire.
# The principal says who is asking; the domain says whose entries are being read, and today
# nothing constrains the second -- see the ACL gap in `common.require_key`.
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
    """Look up the label for `identifier`, returning `(label, note)`.

    `principal` is the calling firmware module, checked against the capability list above.
    `domain` is the WARD domain to read, defaulting to the principal -- an app that reads
    its own entries passes nothing, and `display_address` passes the domain it was asked
    about, which is why the two are separate arguments rather than one.

    `label` is None whenever nothing could be shown, for any reason; `note` always says
    which reason. Raises only if the lookup could not be PERFORMED -- see the module
    docstring on who absorbs that.
    """
    from . import offline_store
    from . import round as sync_round
    from .common import pull_entry, require_initialized
    from .keys import ENTRY_TYPE_ADDRESS, entry_key_for

    _authorize(principal, "read")
    require_initialized()

    app_id = domain if domain is not None else principal
    if key_type is None:
        key_type = ENTRY_TYPE_ADDRESS

    entry_key = await entry_key_for(app_id, identifier, key_type)

    if sync_round.is_online():
        value = await pull_entry(entry_key, key_type)
        # ABSENT is a proven answer here, not a failure: the host had to exhibit a witness
        # for it. An entry whose value is EMPTY is a different thing and keeps its note --
        # it is a label the user chose to blank, and saying "no label" of it would hide a
        # deliberate state.
        if value is None:
            return None, NOTE_ABSENT
        return value, NOTE_UNVERIFIED

    status, entry = await offline_store.get(entry_key)

    if status == offline_store.CORRUPT:
        # NOT reported as "no label". Something is stored at this path that this build
        # cannot read, and the two lead to opposite conclusions about whether the address
        # is known to the wallet.
        return None, NOTE_CORRUPT

    if status == offline_store.MISS or entry is None:
        return None, NOTE_NO_COPY

    if entry.pending:
        return entry.value, NOTE_PENDING

    return entry.value, NOTE_STALE if entry.stale else NOTE_OFFLINE
