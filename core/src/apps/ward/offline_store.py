"""The device's own entries: pinned copies of leaves, and writes it could not publish.

WHAT THIS IS FOR. Until now the device held nothing and every read was a host pull. That works
only for a host that speaks WARD. A host that does not never sends `WardSync`, cannot answer
`WardEntryRequest`, and has no replica to consult -- so serving it means serving from here.

ONE RECORD TYPE, TWO ROLES. A pinned read and an unpublished write differ by one flag. They are
the same wallet's entry at the same path, found the same way and erased the same way; two stores
would have meant two capacity budgets, two lookup paths, and two chances to key one of them
wrong. `FLAG_PENDING` says which one a record is, and the export path clears it -- see
`flush_queue.py`.

THREE ANSWERS, NEVER TWO. `get` returns MISS, VALID or CORRUPT, and the third is the point:
a record this build cannot read must not be reported as absent. "There is nothing here" and
"there is something here and I cannot vouch for it" lead to opposite actions -- the first
invites writing something new over the top, the second must stop and ask -- and collapsing them
loses the distinction in the direction that destroys data.

WHAT AUTHENTICATES A RECORD, given that they are stored in the clear. Not us: `storage.c`
encrypts every protected value under a PIN-derived key with THE SLOT NUMBER AS AAD, over a
global authentication sum across all keys, and faults on a tag mismatch. So tampering, moving a
record between slots, and reading without the PIN are already handled a layer down, and CORRUPT
here means only what that layer cannot know about: an unrecognised format version, or framing
that does not parse. See `storage/ward.py` for why re-sealing under K_data was not worth a
second copy of protections that already exist.

STALENESS IS DERIVED, NEVER STORED. A record carries the counter it was authenticated at; how
stale that is depends on the counter the device trusts NOW, which changes without the record
changing. Computing it at read time means advancing the head can never require touching a
record -- which is what keeps the erase rule true, because a head that had to rewrite records
would eventually be given a reason to delete one.
"""

from micropython import const

MISS = const(0)
VALID = const(1)
CORRUPT = const(2)


class StoredEntry:
    """One record, opened. Never a bare value -- see the staleness note in the module docstring.

    A caller handed only `value` cannot tell a copy confirmed at the current counter from one
    pinned before the device had a root at all, and both reach the same screen. Carrying the
    counter and the two booleans forces the screen to say which it is showing.
    """

    def __init__(
        self,
        entry_key: bytes,
        key_type: str,
        app_id: str,
        identifier: bytes,
        device_id: int,
        value: bytes,
        counter: int,
        pending: bool,
        stale: bool,
    ) -> None:
        self.entry_key = entry_key
        self.key_type = key_type
        self.app_id = app_id
        self.identifier = identifier
        self.device_id = device_id
        self.value = value
        self.counter = counter
        self.pending = pending
        self.stale = stale


def _u16(value: int) -> bytes:
    return value.to_bytes(2, "big")


def encode_record(
    wallet_id: bytes,
    entry_key: bytes,
    key_type: str,
    app_id: str,
    identifier: bytes,
    device_id: int,
    value: bytes,
    counter: int,
    pending: bool,
) -> bytes:
    """The canonical bytes of one record. The only place a record becomes bytes.

    Layout, after the frozen prefix `storage.ward.store_prefix` supplies:

        flags(1) || counter(4 BE) || device_id(1)
        || len8(key_type) || key_type
        || len8(app_id) || app_id
        || len16(identifier) || identifier
        || len16(value) || value

    THE IDENTITY PREIMAGE IS STORED, not a sealed identity part. `app_id`, `identifier` and
    `device_id` are exactly `leaf.pack_identity`'s inputs, so the export path can seal the
    identity part when it needs one -- and the erase screen can name the domain and the key
    with no host to ask, which is the whole point of confirming a deletion by what is being
    lost rather than by an opaque path.

    Being canonical is load-bearing beyond tidiness: a refresh that produces IDENTICAL bytes
    must be recognised as a no-op, so that re-reading an unchanged entry neither prompts the
    user nor rewrites flash. Two encoders would make that comparison meaningless.
    """
    from storage.ward import store_prefix
    from trezor.wire import DataError

    kt = key_type.encode()
    ai = app_id.encode()
    if len(kt) > 0xFF or len(ai) > 0xFF:
        raise DataError("WARD: key_type or app_id too long to store")
    if len(identifier) > 0xFFFF or len(value) > 0xFFFF:
        raise DataError("WARD: identifier or value too long to store")

    return (
        store_prefix(wallet_id, entry_key)
        + bytes([0x01 if pending else 0x00])
        + counter.to_bytes(4, "big")
        + bytes([device_id])
        + bytes([len(kt)])
        + kt
        + bytes([len(ai)])
        + ai
        + _u16(len(identifier))
        + identifier
        + _u16(len(value))
        + value
    )


def _parse(record: bytes, trusted_counter: int) -> StoredEntry:
    """Bytes back to a StoredEntry, or raise. Only `get` calls this, and it catches."""
    from storage.ward import STORE_KEY_OFF, STORE_PREFIX_LEN
    from trezor.wire import DataError

    entry_key = record[STORE_KEY_OFF:STORE_PREFIX_LEN]
    off = STORE_PREFIX_LEN
    flags = record[off]
    counter = int.from_bytes(record[off + 1 : off + 5], "big")
    device_id = record[off + 5]
    off += 6

    def take(n: int) -> bytes:
        nonlocal off
        chunk = record[off : off + n]
        # A slice past the end is SHORT, not an error, so every field checks its own width --
        # otherwise a truncated record parses into plausible short strings and reaches a screen.
        if len(chunk) != n:
            raise DataError("WARD: truncated record")
        off += n
        return chunk

    key_type = take(take(1)[0]).decode()
    app_id = take(take(1)[0]).decode()
    identifier = take(int.from_bytes(take(2), "big"))
    value = take(int.from_bytes(take(2), "big"))
    if off != len(record):
        raise DataError("WARD: trailing bytes in record")

    return StoredEntry(
        entry_key=entry_key,
        key_type=key_type,
        app_id=app_id,
        identifier=identifier,
        device_id=device_id,
        value=value,
        counter=counter,
        pending=bool(flags & 0x01),
        # A record pinned before the device had any root carries counter 0, so it turns stale
        # the instant a reconcile moves the trusted counter off zero, and stays that way. That
        # falls out of the comparison and needs no flag: what was authenticated against nothing
        # can never be current once there is something to be current against.
        stale=counter < trusted_counter,
    )


async def get(entry_key: bytes) -> "tuple[int, StoredEntry | None]":
    """(status, entry). CORRUPT never degrades to MISS, and nothing here ever deletes."""
    from storage import ward as ward_store

    from .keys import derive_wallet_id
    from .root import get_counter

    record = ward_store.store_get(await derive_wallet_id(), entry_key)
    if record is None:
        return MISS, None

    # An unknown version is REPORTED, not removed. A newer firmware may have written this, and
    # the user may want it back by downgrading -- destroying it to tidy up would be a migration
    # that silently loses data, which is the one thing the erase rule forbids outright.
    if record[0] != ward_store.STORE_VERSION:
        return CORRUPT, None

    try:
        return VALID, _parse(record, await get_counter())
    except Exception:
        # Framing that does not parse. Caught broadly on purpose: every way of failing to read
        # a record means the same thing to a caller, and a new failure mode leaking out as an
        # unhandled exception would surface as a generic firmware error rather than as
        # "there is something here that cannot be read".
        return CORRUPT, None


async def put(
    entry_key: bytes,
    key_type: str,
    app_id: str,
    identifier: bytes,
    device_id: int,
    value: bytes,
    counter: int,
    pending: bool,
) -> None:
    """Write a record. Raises when the store is full -- it never makes room."""
    from storage import ward as ward_store
    from trezor.wire import DataError

    from .keys import derive_wallet_id

    if len(value) > ward_store.MAX_VALUE_LEN:
        raise DataError("WARD: value too large to keep offline")

    wallet_id = await derive_wallet_id()
    record = encode_record(
        wallet_id,
        entry_key,
        key_type,
        app_id,
        identifier,
        device_id,
        value,
        counter,
        pending,
    )
    if not ward_store.store_put(wallet_id, entry_key, record):
        # Full means FULL. No eviction, so the user is told and chooses what to give up --
        # every occupant is either something they pinned or a change they confirmed.
        raise DataError("WARD: offline store is full; erase an entry first")


async def erase(entry_key: bytes) -> None:
    """Remove a record. THE CALLER MUST ALREADY HOLD THE USER'S CONFIRMATION.

    No check here enforces that, deliberately -- see `storage.ward.store_delete`. The rule is
    kept by there being exactly one caller, `erase_cached_entry`, whose entire body is the
    confirmation.
    """
    from storage import ward as ward_store

    from .keys import derive_wallet_id

    ward_store.store_delete(await derive_wallet_id(), entry_key)


async def list_entries() -> "list[StoredEntry]":
    """Every readable record of the ACTIVE wallet, in slot order.

    Scoped to one wallet with no argument to widen it: enumeration is where a missing filter
    leaks the existence of another hidden wallet's entries rather than merely failing.

    A LIST, not a generator. An async generator would suspend inside a loop that is reading
    flash, and the store is small enough that the whole of it costs less than the machinery
    would -- eight records, bounded by MAX_VALUE_LEN each.

    Unreadable records are SKIPPED here, not deleted and not raised on: enumeration is a
    background question ("what is pending?"), and one bad record must not make the rest
    unreachable. Naming a corrupt record is `get`'s job, where a caller asked about it.
    """
    from storage import ward as ward_store

    from .keys import derive_wallet_id
    from .root import get_counter

    trusted = await get_counter()
    out = []
    for record in ward_store.store_list(await derive_wallet_id()):
        if record[0] != ward_store.STORE_VERSION:
            continue
        try:
            out.append(_parse(record, trusted))
        except Exception:
            continue
    return out


# A PENDING RECORD HAS TWO SUB-STATES, and the assigned counter tells them apart:
#
#   counter == 0 : queued, never handed to a host. This is what `flush_queue` looks for.
#   counter == N : handed over, claiming to become counter N, not yet confirmed by the WM.
#
# Only the first is re-offered, which is what stops a flush loop from publishing the same
# record forever -- the host repeats while `remaining` is non-zero, and a record that has just
# been exported must not still be counted as waiting to go.
#
# The second state resolves at the next reconcile, and only there, because that is the only
# moment the device learns what the head actually became. See `reconcile_pending`.


async def next_unsent() -> "StoredEntry | None":
    """The oldest queued write that has not been handed to a host yet, or None."""
    for entry in await list_entries():
        if entry.pending and entry.counter == 0:
            return entry
    return None


async def count_unsent() -> int:
    """How many queued writes are still waiting to be handed over."""
    n = 0
    for entry in await list_entries():
        if entry.pending and entry.counter == 0:
            n += 1
    return n


async def reconcile_pending(adopted: int) -> None:
    """Settle every exported-but-unconfirmed write against the head just adopted.

    This is the ONLY place a queued write stops being queued, and it runs at the same boundary
    an online write commits at: the head moves when the WM confirms a counter, not when a host
    says it stored something. Two outcomes, both REWRITES and neither a delete:

      assigned <= adopted : the change landed. Drop the flag; the record stays as the cached
                            copy of the value now in the tree, at a counter the device trusts.

      assigned >  adopted : the head did not reach it, so the host never published it. Reset
                            the assigned counter to 0 so `flush_queue` offers it again. Without
                            this a lost or dropped publication would strand the change forever
                            -- still stored, never re-sent, and invisible to the user as a
                            problem.

    Records at counter 0 are untouched: zero means "no counter assigned", not "counter zero".

    KNOWN LIMITATION. "The head reached N" is not quite "my change is what made it N". If
    another device of this wallet advanced the counter first, this clears a record whose change
    did not land, and the value survives only as a cached copy that will read as stale. The
    divergence itself is caught by reconcile's same-counter-different-root check; distinguishing
    the two properly needs a membership proof per queued change, which is more machinery than
    one-intent-per-round-trip currently earns.
    """
    from storage import ward as ward_store

    from .keys import derive_wallet_id

    wallet_id = await derive_wallet_id()
    for entry in await list_entries():
        if not entry.pending or entry.counter == 0:
            continue
        landed = entry.counter <= adopted
        ward_store.store_put(
            wallet_id,
            entry.entry_key,
            encode_record(
                wallet_id,
                entry.entry_key,
                entry.key_type,
                entry.app_id,
                entry.identifier,
                entry.device_id,
                entry.value,
                entry.counter if landed else 0,
                not landed,
            ),
        )
