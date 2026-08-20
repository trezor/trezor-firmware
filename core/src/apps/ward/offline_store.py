"""The device's own entries: pinned copies of leaves, and writes it could not publish.

WHAT THIS IS FOR. Until now the device held nothing and every read was a host pull. That works
only for a host that speaks WARD. A host that does not never sends `WardSync`, cannot answer
`WardEntryRequest`, and has no replica to consult -- so serving it means serving from here.

ONE RECORD TYPE, TWO ROLES. A pinned read and an unpublished write differ by one flag. They are
the same wallet's entry under the same identity, found the same way and erased the same way; two
stores would have meant two capacity budgets, two lookup paths, and two chances to key one of them
wrong. `FLAG_PENDING` says which one a record is, and `reconcile_pending` clears it.

NAMED BY IDENTITY, NOT BY THE KEYED PATH. A record carries (key_type, app_id, identifier) and is
found by them. `entry_key` is where a leaf sits in the TRIE and is assigned when a change is
published; a queued change has not been published, so it has no path to store, and storing one for
the pinned case only would have meant two shapes in the one record type this file exists to keep
single. Every caller that needs a path derives it -- `keys.entry_key_for(app_id, identifier,
key_type)` -- at the moment the trie is involved, which for a queued change is `flush_queue`.

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

THE STORED wallet_id IS TRUNCATED, and `storage.ward` is where that happens -- this file hands over
the whole 16-byte id and never has to know. 56 bits tells one wallet's records from another's on this
device, which is all the tag does; the argument is in `storage.ward._STORE_WALLET_ID_LEN`.

NO COUNTER IS STORED, so nothing here reports staleness. A record used to carry the counter it was
authenticated at, and a read compared that against the counter the device trusted to decide whether
the value might be behind. That comparison is gone with the field: a pinned copy now says only that
it has not been checked against a host, which is the honest floor. What the counter also did --
telling a change already handed to a host from one still waiting -- is `FLAG_OFFERED` now.
"""

from micropython import const

MISS = const(0)
VALID = const(1)
CORRUPT = const(2)


class StoredEntry:
    """One record, opened.

    Carries the whole identity rather than a value alone: the screens have to name the domain and
    the key of what they are about, and `flush_queue` needs the identity to derive the path the
    change will be published at.
    """

    def __init__(
        self,
        key_type: str,
        app_id: str,
        identifier: bytes,
        value: bytes,
        pending: bool,
        offered: bool,
    ) -> None:
        self.key_type = key_type
        self.app_id = app_id
        self.identifier = identifier
        self.value = value
        self.pending = pending
        self.offered = offered


def _u16(value: int) -> bytes:
    return value.to_bytes(2, "big")


def identity_block(key_type: str, app_id: str, identifier: bytes) -> bytes:
    """The canonical bytes a record is FOUND by:

        len8(key_type) || key_type || len8(app_id) || app_id || len16(identifier) || identifier

    Length-prefixed rather than concatenated, for the reason `leaf.leaf_hash_of` gives: adjacent
    variable-length fields leave their boundary ambiguous, so ("ab", "c") and ("a", "bc") would
    otherwise match each other's records.

    Canonical is load-bearing twice over. It is the lookup key, so two encoders would mean a record
    written by one and searched for by the other is lost while still occupying a slot; and it sits
    inside the frozen header (see `storage.ward`), so a build that cannot parse the rest of a record
    can still find it by this much.
    """
    from trezor.wire import DataError

    kt = key_type.encode()
    ai = app_id.encode()
    if len(kt) > 0xFF or len(ai) > 0xFF:
        raise DataError("WARD: key_type or app_id too long to store")
    if len(identifier) > 0xFFFF:
        raise DataError("WARD: identifier too long to store")

    return (
        bytes([len(kt)]) + kt + bytes([len(ai)]) + ai + _u16(len(identifier)) + identifier
    )


def encode_record(
    wallet_id: bytes,
    key_type: str,
    app_id: str,
    identifier: bytes,
    value: bytes,
    pending: bool,
    offered: bool = False,
) -> bytes:
    """The canonical bytes of one record. The only place a record becomes bytes.

    Layout, after the frozen prefix `storage.ward.store_prefix` supplies:

        identity_block(key_type, app_id, identifier) || flags(1) || len16(value) || value

    THE IDENTITY IS STORED, and it is stored FIRST because it is what the record is found by. It is
    also exactly what `leaf.pack_identity` needs, so the export path can seal the identity part when
    it needs one -- and the erase screen can name the domain and the key with no host to ask, which
    is the whole point of confirming a deletion by what is being lost rather than by an opaque path.

    Being canonical is load-bearing beyond tidiness: a refresh that produces IDENTICAL bytes must be
    recognised as a no-op, so that re-reading an unchanged entry neither prompts the user nor
    rewrites flash. Two encoders would make that comparison meaningless.
    """
    from storage.ward import FLAG_OFFERED, FLAG_PENDING, store_prefix
    from trezor.wire import DataError

    if len(value) > 0xFFFF:
        raise DataError("WARD: value too long to store")

    flags = (FLAG_PENDING if pending else 0) | (FLAG_OFFERED if offered else 0)

    return (
        store_prefix(wallet_id)
        + identity_block(key_type, app_id, identifier)
        + bytes([flags])
        + _u16(len(value))
        + value
    )


def _parse(record: bytes) -> StoredEntry:
    """Bytes back to a StoredEntry, or raise. Only `get` and `list_entries` call this."""
    from storage.ward import FLAG_OFFERED, FLAG_PENDING, STORE_KEY_OFF
    from trezor.wire import DataError

    off = STORE_KEY_OFF

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
    flags = take(1)[0]
    value = take(int.from_bytes(take(2), "big"))
    if off != len(record):
        raise DataError("WARD: trailing bytes in record")

    return StoredEntry(
        key_type=key_type,
        app_id=app_id,
        identifier=identifier,
        value=value,
        pending=bool(flags & FLAG_PENDING),
        offered=bool(flags & FLAG_OFFERED),
    )


async def get(
    key_type: str, app_id: str, identifier: bytes
) -> "tuple[int, StoredEntry | None]":
    """(status, entry). CORRUPT never degrades to MISS, and nothing here ever deletes."""
    from storage import ward as ward_store

    from .keys import derive_wallet_id

    wallet_id = await derive_wallet_id()
    identity = identity_block(key_type, app_id, identifier)
    record = ward_store.store_get(wallet_id, identity)

    if record is None:
        # A record written by a NEWER build carries its identity in a layout this one does not know,
        # so it cannot be matched -- and reporting MISS would invite writing over it. Refusing while
        # any unreadable record of this wallet exists is deliberately conservative: it is a refusal,
        # never a deletion, and it clears the moment the user erases that record.
        if ward_store.store_find_unreadable(wallet_id) is not None:
            return CORRUPT, None
        return MISS, None

    # An unknown version is REPORTED, not removed. A newer firmware may have written this, and
    # the user may want it back by downgrading -- destroying it to tidy up would be a migration
    # that silently loses data, which is the one thing the erase rule forbids outright.
    if record[0] != ward_store.STORE_VERSION:
        return CORRUPT, None

    try:
        return VALID, _parse(record)
    except Exception:
        # Framing that does not parse. Caught broadly on purpose: every way of failing to read
        # a record means the same thing to a caller, and a new failure mode leaking out as an
        # unhandled exception would surface as a generic firmware error rather than as
        # "there is something here that cannot be read".
        return CORRUPT, None


def ensure_storable(
    key_type: str, app_id: str, identifier: bytes, value: bytes
) -> None:
    """Raise unless this entry would fit, WITHOUT writing anything.

    SIZE IS REFUSED BEFORE THE PROMPT, which is why this is separate from `put`. Asking the user to
    confirm something and then failing to store it wastes a confirmation and teaches them the screen
    means nothing -- the same reason `pin_cached_entry` checks up front and the same reason a restore
    verifies its MAC before showing anything.

    `put` checks both caps again. That is not redundancy for its own sake: `put` is the only writer,
    so its checks are what actually hold the format's promises, and this one exists so that a caller
    with a screen to show can find out early.
    """
    from storage import ward as ward_store
    from trezor.wire import DataError

    if len(value) > ward_store.MAX_VALUE_LEN:
        raise DataError("WARD: value too large to keep offline")

    # The identity framing counts too: a long app_id or identifier can push a legal value past the
    # record cap. Measured rather than estimated -- the encoder is the only authority on a record's
    # size, and a wallet_id of the right width is all it needs to measure one.
    record = encode_record(
        bytes(16), key_type, app_id, identifier, value, False, False
    )
    if len(record) > ward_store.MAX_RECORD_LEN:
        raise DataError("WARD: entry too large to keep offline")


async def put(
    key_type: str,
    app_id: str,
    identifier: bytes,
    value: bytes,
    pending: bool,
    offered: bool = False,
) -> None:
    """Write a record. Raises when the store is full -- it never makes room."""
    from storage import ward as ward_store
    from trezor.wire import DataError

    from .keys import derive_wallet_id

    if len(value) > ward_store.MAX_VALUE_LEN:
        raise DataError("WARD: value too large to keep offline")

    wallet_id = await derive_wallet_id()
    record = encode_record(
        wallet_id, key_type, app_id, identifier, value, pending, offered
    )
    # The value cap alone does not bound a record: app_id and identifier have their own framing, so a
    # long enough pair would make one record eat most of the store's byte budget while every
    # individual field looked legal. See `storage.ward.MAX_RECORD_LEN`.
    if len(record) > ward_store.MAX_RECORD_LEN:
        raise DataError("WARD: entry too large to keep offline")
    if not ward_store.store_put(
        wallet_id, identity_block(key_type, app_id, identifier), record
    ):
        # Full means FULL, whether it ran out of slots or of the byte budget -- both mean the same
        # thing to whoever asked. No eviction, so the user is told and chooses what to give up: every
        # occupant is either something they pinned or a change they confirmed.
        raise DataError("WARD: offline store is full; erase an entry first")


async def erase(key_type: str, app_id: str, identifier: bytes) -> None:
    """Remove a record. THE CALLER MUST ALREADY HOLD THE USER'S CONFIRMATION.

    No check here enforces that, deliberately -- see `storage.ward.store_delete`. The rule is
    kept by there being exactly two callers, `erase_cached_entry` and `queue_delete_entry`, whose
    entire bodies are the confirmation.
    """
    from storage import ward as ward_store

    from .keys import derive_wallet_id

    ward_store.store_delete(
        await derive_wallet_id(), identity_block(key_type, app_id, identifier)
    )


async def erase_unreadable() -> bool:
    """Remove one record this build cannot parse, if there is one. True if something went.

    THE CALLER MUST ALREADY HOLD THE USER'S CONFIRMATION, as with `erase`. Such a record cannot be
    named -- that is what makes it unreadable -- so the only handle left is the slot it occupies,
    and without this path it would hold that slot forever.
    """
    from storage import ward as ward_store

    from .keys import derive_wallet_id

    index = ward_store.store_find_unreadable(await derive_wallet_id())
    if index is None:
        return False
    ward_store.store_delete_slot(index)
    return True


async def list_entries() -> "list[StoredEntry]":
    """Every readable record of the ACTIVE wallet, in slot order.

    Scoped to one wallet with no argument to widen it: enumeration is where a missing filter
    leaks the existence of another hidden wallet's entries rather than merely failing.

    A LIST, not a generator. An async generator would suspend inside a loop that is reading
    flash, and the store is small enough that the whole of it costs less than the machinery
    would -- twenty records at most, and `storage.ward.MAX_STORE_BYTES` of them in total.

    Unreadable records are SKIPPED here, not deleted and not raised on: enumeration is a
    background question ("what is pending?"), and one bad record must not make the rest
    unreachable. Naming a corrupt record is `get`'s job, where a caller asked about it.
    """
    from storage import ward as ward_store

    from .keys import derive_wallet_id

    out = []
    for record in ward_store.store_list(await derive_wallet_id()):
        if record[0] != ward_store.STORE_VERSION:
            continue
        try:
            out.append(_parse(record))
        except Exception:
            continue
    return out


# A PENDING RECORD HAS TWO SUB-STATES, and `FLAG_OFFERED` tells them apart:
#
#   not offered : queued, never handed to a host. This is what `flush_queue` looks for.
#   offered     : handed over, not yet confirmed by the WM.
#
# Only the first is re-offered, which is what stops a flush loop from publishing the same record
# forever -- the host repeats while `remaining` is non-zero, and a record that has just been
# exported must not still be counted as waiting to go.
#
# The second state resolves at the next reconcile, and only there, because that is the only moment
# the device learns the head moved at all. See `reconcile_pending`.
#
# This used to be a stored COUNTER: zero meant "not offered" and N meant "offered, claiming to
# become N". The flag keeps both sub-states in one bit; the claim itself moved to the session cache,
# where `mark_offered` puts it and `reconcile_pending` reads it.


async def next_unsent() -> "StoredEntry | None":
    """The oldest queued write that has not been handed to a host yet, or None."""
    for entry in await list_entries():
        if entry.pending and not entry.offered:
            return entry
    return None


async def count_unsent() -> int:
    """How many queued writes are still waiting to be handed over."""
    n = 0
    for entry in await list_entries():
        if entry.pending and not entry.offered:
            n += 1
    return n


# WHERE THE CLAIM LIVES, now that no record stores a counter.
#
# A flush hands a change over CLAIMING a counter, and only a comparison against the head actually
# adopted can say whether that claim was met. The claim is per-change, so `FLAG_OFFERED` alone cannot
# carry it -- and putting it back in the record is exactly what this format dropped.
#
# So it lives in the SESSION CACHE: slot(1) || claimed counter(4 BE), up to 8 of them. That lifetime
# is not a compromise, it is the safe one. A session that drops loses the claims, and a claim the
# device cannot attribute is treated as NOT LANDED -- so the change is offered again. Fail-closed in
# the direction that costs a re-send rather than a change.


def _claims() -> dict:
    """{slot: claimed counter} for this session, or empty if nothing has been offered."""
    from storage.cache_common import APP_WARD_OFFERS
    from trezor.wire import context

    raw = context.cache_get(APP_WARD_OFFERS) or b""
    out = {}
    for i in range(0, len(raw) - 4, 5):
        slot = raw[i]
        if slot != 0xFF:
            out[slot] = int.from_bytes(raw[i + 1 : i + 5], "big")
    return out


def _set_claims(claims: dict) -> None:
    from storage.cache_common import APP_WARD_OFFERS
    from trezor.wire import context

    raw = bytearray(b"\xff" * 40)
    for i, (slot, counter) in enumerate(sorted(claims.items())[:8]):
        raw[i * 5] = slot
        raw[i * 5 + 1 : i * 5 + 5] = counter.to_bytes(4, "big")
    context.cache_set(APP_WARD_OFFERS, bytes(raw))


async def mark_offered(entry: StoredEntry, counter: int) -> None:
    """Record that this queued change has been handed to a host, keeping it PENDING.

    Two writes, deliberately in different places: the FLAG goes to flash, so a dropped session does
    not make the device offer the same change again inside one flush loop; the CLAIMED COUNTER goes to
    the session cache, because it is the thing a reconcile compares and the thing a record must not
    hold. Both happen before the ack goes out.

    It stays pending either way: handing the leaf over is not the change taking effect -- the head
    moves when the WM confirms, which is `reconcile`'s job.
    """
    await put(
        entry.key_type, entry.app_id, entry.identifier, entry.value, True, offered=True
    )

    # The SLOT is the handle a claim is filed under: it is one byte, stable while the record lives,
    # and the record is already written by the time this runs.
    from storage import ward as ward_store

    from .keys import derive_wallet_id

    slot = ward_store.store_find(
        await derive_wallet_id(),
        identity_block(entry.key_type, entry.app_id, entry.identifier),
    )
    if slot is not None:
        claims = _claims()
        claims[slot] = counter
        _set_claims(claims)


async def reconcile_pending(adopted: int) -> None:
    """Settle every offered-but-unconfirmed write against the head just adopted.

    This is the ONLY place a queued write stops being queued, and it runs at the same boundary an
    online write commits at: the head moves when the WM confirms a counter, not when a host says it
    stored something. Three outcomes, all REWRITES and none a delete:

      claimed <= adopted : the change landed. Both flags go; the record stays as the cached copy of
                           the value now in the tree.

      claimed >  adopted : the head did not reach it, so the host never published it. The OFFERED
                           flag goes and the record stays PENDING, so `flush_queue` offers it again.
                           Without this a lost or dropped publication would strand the change forever
                           -- still stored, never re-sent, invisible to the user as a problem.

      no claim recorded  : the session that offered it is gone, so the device cannot attribute the
                           change either way. Treated as NOT LANDED, for the same reason: a re-send
                           costs a round trip, a wrong clear costs the change.

    Records that were never offered are untouched.

    KNOWN LIMITATION. "The head reached N" is not quite "my change is what made it N". If another
    device of this wallet advanced the counter first, this clears a record whose change did not land,
    and the value survives only as a cached copy. The divergence itself is caught by reconcile's
    same-counter-different-root check; distinguishing the two properly needs a membership proof per
    queued change, which is more machinery than one-intent-per-round-trip currently earns.
    """
    from storage import ward as ward_store

    from .keys import derive_wallet_id

    wallet_id = await derive_wallet_id()
    claims = _claims()
    for entry in await list_entries():
        if not entry.pending or not entry.offered:
            continue
        slot = ward_store.store_find(
            wallet_id, identity_block(entry.key_type, entry.app_id, entry.identifier)
        )
        claimed = claims.get(slot) if slot is not None else None
        landed = claimed is not None and claimed <= adopted
        ward_store.store_put(
            wallet_id,
            identity_block(entry.key_type, entry.app_id, entry.identifier),
            encode_record(
                wallet_id,
                entry.key_type,
                entry.app_id,
                entry.identifier,
                entry.value,
                not landed,
                False,
            ),
        )
