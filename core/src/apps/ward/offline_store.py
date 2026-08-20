"""The device's own entries: pinned copies of leaves, and writes it could not publish.

WHAT THIS IS FOR. Until now the device held nothing and every read was a host pull. That works
only for a host that speaks WARD. A host that does not never sends `WardSync`, cannot answer
`WardEntryRequest`, and has no replica to consult -- so serving it means serving from here.

ONE RECORD TYPE, TWO ROLES. A pinned read and an unpublished write differ by one flag. They are
the same wallet's entry under the same identity, found the same way and erased the same way; two
stores would have meant two capacity budgets, two lookup paths, and two chances to key one of them
wrong. `FLAG_PENDING` says which one a record is, and `reconcile_pending` clears it.

TWO FORMS OF THE SAME RECORD. The FULL form carries the identity; the COMPACT form carries
`keys.wallet_entry` -- a hash of it -- and no wallet tag either, since that hash already commits to
wallet_id. It is 47 bytes smaller for a typical address. Everything that reaches this module already
knows the identity, so both forms are found the same way: compute both names and match either.

WHAT THE MISSING TAG COSTS: nothing can ask "whose is this compact record?" without the identity. So
enumeration (`list_entries`) returns only full-form records, `count_unsent` counts what can be
published UNPROMPTED, and a reconcile settles records through the session claim ledger, which names
slots this wallet offered itself. A compact record is reachable by name and by slot, never by sweep.

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
        compact: bool = False,
        slot: "int | None" = None,
        raw: bytes = b"",
    ) -> None:
        self.key_type = key_type
        self.app_id = app_id
        self.identifier = identifier
        self.value = value
        self.pending = pending
        self.offered = offered
        # A compact record does not store its identity: the three fields above were filled in from
        # whoever asked. Kept as a flag rather than left implicit, because `flush_queue` has to know
        # that it cannot get an identity from this record on its own.
        self.compact = compact
        # The slot and the bytes that came out of it, for the two operations that change only FLAGS.
        # They rewrite what is there rather than re-encoding, because re-encoding needs an identity
        # and a compact record has none to give.
        self.slot = slot
        self.raw = raw


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


async def _candidates(
    key_type: str, app_id: str, identifier: bytes
) -> "list[tuple[int, bytes]]":
    """Both names an entry can be stored under: its identity, and the hash that stands in for it.

    Passing both to one lookup is what makes the two forms interchangeable to every caller here.
    Order matters only for speed -- the full form is the common one, so it is tried first.
    """
    from storage.ward import STORE_VERSION, STORE_VERSION_COMPACT

    from .keys import derive_wallet_id, wallet_entry

    return [
        (STORE_VERSION, identity_block(key_type, app_id, identifier)),
        (
            STORE_VERSION_COMPACT,
            wallet_entry(await derive_wallet_id(), app_id, identifier, key_type),
        ),
    ]


def encode_record(
    wallet_id: bytes,
    key_type: str,
    app_id: str,
    identifier: bytes,
    value: bytes,
    pending: bool,
    offered: bool = False,
    compact: bool = False,
) -> bytes:
    """The canonical bytes of one record. The only place a record becomes bytes.

    Layout, after the frozen prefix `storage.ward.store_prefix` supplies:

        full     identity_block(key_type, app_id, identifier) || flags(1) || len16(value) || value
        compact  wallet_entry(16)                             || flags(1) || len16(value) || value

    THE IDENTITY IS STORED, and it is stored FIRST because it is what the record is found by. It is
    also exactly what `leaf.pack_identity` needs, so the export path can seal the identity part when
    it needs one -- and the erase screen can name the domain and the key with no host to ask, which
    is the whole point of confirming a deletion by what is being lost rather than by an opaque path.

    Being canonical is load-bearing beyond tidiness: a refresh that produces IDENTICAL bytes must be
    recognised as a no-op, so that re-reading an unchanged entry neither prompts the user nor
    rewrites flash. Two encoders would make that comparison meaningless.
    """
    from storage.ward import (
        FLAG_OFFERED,
        FLAG_PENDING,
        STORE_VERSION,
        STORE_VERSION_COMPACT,
        store_prefix,
    )
    from trezor.wire import DataError

    from .keys import wallet_entry

    if len(value) > 0xFFFF:
        raise DataError("WARD: value too long to store")

    flags = (FLAG_PENDING if pending else 0) | (FLAG_OFFERED if offered else 0)

    if compact:
        version = STORE_VERSION_COMPACT
        name = wallet_entry(wallet_id, app_id, identifier, key_type)
    else:
        version = STORE_VERSION
        name = identity_block(key_type, app_id, identifier)

    return (
        store_prefix(wallet_id, version)
        + name
        + bytes([flags])
        + _u16(len(value))
        + value
    )


def _parse(
    record: bytes,
    key_type: str | None = None,
    app_id: str | None = None,
    identifier: bytes | None = None,
    slot: "int | None" = None,
) -> StoredEntry:
    """Bytes back to a StoredEntry, or raise. Only `get` and `list_entries` call this.

    A COMPACT record has no identity to parse, so the caller's is used -- `get` has it from the
    request and has just proved it hashes to what the record is named by. `list_entries` has none,
    which is why a compact record comes back from there with empty identity fields and its `compact`
    flag set: enumeration can count and settle such a record, but only a caller who names the entry
    can say what it is.
    """
    from storage.ward import FLAG_OFFERED, FLAG_PENDING, STORE_VERSION_COMPACT
    from trezor.wire import DataError

    from .keys import WALLET_ENTRY_LEN

    off = ward_store_key_off(record)

    def take(n: int) -> bytes:
        nonlocal off
        chunk = record[off : off + n]
        # A slice past the end is SHORT, not an error, so every field checks its own width --
        # otherwise a truncated record parses into plausible short strings and reaches a screen.
        if len(chunk) != n:
            raise DataError("WARD: truncated record")
        off += n
        return chunk

    compact = record[0] == STORE_VERSION_COMPACT
    if compact:
        take(WALLET_ENTRY_LEN)  # the hash the record is named by; nothing to read out of it
    else:
        key_type = take(take(1)[0]).decode()
        app_id = take(take(1)[0]).decode()
        identifier = take(int.from_bytes(take(2), "big"))
    flags = take(1)[0]
    value = take(int.from_bytes(take(2), "big"))
    if off != len(record):
        raise DataError("WARD: trailing bytes in record")

    return StoredEntry(
        key_type=key_type if key_type is not None else "",
        app_id=app_id if app_id is not None else "",
        identifier=identifier if identifier is not None else b"",
        value=value,
        pending=bool(flags & FLAG_PENDING),
        offered=bool(flags & FLAG_OFFERED),
        compact=compact,
        slot=slot,
        raw=record,
    )


def ward_store_key_off(record: bytes) -> int:
    """Where this record's NAME starts -- the one offset the two forms disagree about."""
    from storage.ward import store_key_off

    return store_key_off(record[0])


def _flags_off(record: bytes) -> int:
    """Where the flags byte sits, whichever form the record is in.

    Derived rather than remembered: the full form's identity is variable length, so the offset has to
    be walked, and having one function do it keeps `_parse` and the flag rewrites from disagreeing
    about where it is.
    """
    from storage.ward import STORE_VERSION_COMPACT

    from .keys import WALLET_ENTRY_LEN

    off = ward_store_key_off(record)
    if record[0] == STORE_VERSION_COMPACT:
        return off + WALLET_ENTRY_LEN

    off += 1 + record[off]  # key_type
    off += 1 + record[off]  # app_id
    off += 2 + int.from_bytes(record[off : off + 2], "big")  # identifier
    return off


def record_commit(record: bytes) -> bytes:
    """A fingerprint of what a record MEANS, with its PENDING/OFFERED flags normalised out.

    This is what lets an offer claim name the exact record GENERATION it was filed for. Slots are
    reused and a queued value can be replaced in place (`queue_set_entry`), so a claim carrying
    only a slot number settles whatever happens to occupy that slot later: offer A, replace it with
    B, watch A land, and B -- which never landed -- is cleared as though it had. That is silent
    local data loss, and comparing this hash is what refuses it.

    THE FLAGS ARE EXCLUDED BECAUSE THEY MOVE. A record is marked OFFERED after its claim is filed
    and loses PENDING when the claim settles, so including them would make a claim stop matching
    the very record it describes. Everything else is included, and a record's NAME already commits
    to the wallet, the app, the identifier and the key type -- in the full form as an identity
    block, in the compact form as a hash over exactly those -- so a change of value, of identity or
    of form all produce a different commitment.
    """
    from trezor.crypto.hashlib import sha256

    off = _flags_off(record)
    h = sha256(b"WARD RECORD v1")
    h.update(record[:off])
    h.update(b"\x00")
    h.update(record[off + 1 :])
    return h.digest()


async def _set_flags(entry: StoredEntry, pending: bool, offered: bool) -> None:
    """Rewrite one record's flags, in place, in whatever form it is stored.

    NO IDENTITY NEEDED, which is the whole reason this exists: `flush_queue` and a reconcile change
    only these two bits, and a compact record could not be re-encoded from what they hold.
    """
    from storage import ward as ward_store

    if entry.slot is None:
        raise ValueError  # only a record that came from `list_entries` can be flipped

    flags = (ward_store.FLAG_PENDING if pending else 0) | (
        ward_store.FLAG_OFFERED if offered else 0
    )
    off = _flags_off(entry.raw)
    ward_store.store_write_slot(
        entry.slot, entry.raw[:off] + bytes([flags]) + entry.raw[off + 1 :]
    )


async def get(
    key_type: str, app_id: str, identifier: bytes
) -> "tuple[int, StoredEntry | None]":
    """(status, entry). CORRUPT never degrades to MISS, and nothing here ever deletes."""
    from storage import ward as ward_store

    from .keys import derive_wallet_id

    wallet_id = await derive_wallet_id()
    # Found by SLOT rather than just by name: the slot travels with the entry, because it is the only
    # handle `mark_offered` and a reconcile can use -- neither can re-find a compact record from an
    # identity it does not carry.
    slot = ward_store.store_find(
        wallet_id, await _candidates(key_type, app_id, identifier)
    )
    record = None if slot is None else ward_store.store_read_slot(slot)

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
    #
    # BOTH FORMS THIS BUILD KNOWS ARE KNOWN. Listing only the full one here made every compact record
    # read as unreadable, which is the failure this check exists to avoid, pointed the wrong way.
    if record[0] not in (ward_store.STORE_VERSION, ward_store.STORE_VERSION_COMPACT):
        return CORRUPT, None

    try:
        # The caller's identity is handed to the parser: a compact record has none of its own, and
        # this is the point at which it is known to be the right one -- the record was FOUND by the
        # hash of exactly these three fields.
        return VALID, _parse(record, key_type, app_id, identifier, slot)
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
    compact: bool = False,
) -> None:
    """Write a record. Raises when the store is full -- it never makes room."""
    from storage import ward as ward_store
    from trezor.wire import DataError

    from .keys import derive_wallet_id

    if len(value) > ward_store.MAX_VALUE_LEN:
        raise DataError("WARD: value too large to keep offline")

    wallet_id = await derive_wallet_id()
    record = encode_record(
        wallet_id, key_type, app_id, identifier, value, pending, offered, compact
    )
    # The value cap alone does not bound a record: app_id and identifier have their own framing, so a
    # long enough pair would make one record eat most of the store's byte budget while every
    # individual field looked legal. See `storage.ward.MAX_RECORD_LEN`.
    if len(record) > ward_store.MAX_RECORD_LEN:
        raise DataError("WARD: entry too large to keep offline")
    candidates = await _candidates(key_type, app_id, identifier)
    version, name = candidates[1] if compact else candidates[0]
    other = candidates[0][1] if compact else candidates[1][1]
    # `replaces` is what lets a record CHANGE FORM in place: written compact over a full record, or
    # the other way round, it must take over the slot rather than leave a second copy of the same
    # entry behind under the other name.
    if not ward_store.store_put(wallet_id, version, name, record, replaces=other):
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
        await derive_wallet_id(), await _candidates(key_type, app_id, identifier)
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
    for slot, record in ward_store.store_list(await derive_wallet_id()):
        if record[0] not in (ward_store.STORE_VERSION, ward_store.STORE_VERSION_COMPACT):
            continue
        try:
            # No identity is passed: enumeration does not know one, so a compact record comes back
            # with its identity fields empty and `compact` set. Everything enumeration is for --
            # counting what is pending, settling it after a reconcile -- works on flags alone.
            out.append(_parse(record, slot=slot))
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
    """The oldest queued write that has not been handed over yet and can be published UNPROMPTED.

    Compact records are absent by construction: enumeration cannot attribute one to a wallet, and a
    flush could not publish it anyway without being told which entry it is. So this answers exactly
    the question the unnamed flush asks.
    """
    for entry in await list_entries():
        if entry.pending and not entry.offered:
            return entry
    return None


async def count_unsent() -> int:
    """How many queued writes are still waiting AND publishable unprompted -- the `remaining` figure.

    A compact record is not counted. It can only be published by name, so the caller holding its
    backup is the authority on how many of those are outstanding; counting them here would tell a host
    to keep looping for changes this device cannot hand it.
    """
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


async def _claim_wallet_id() -> bytes:
    from .keys import derive_wallet_id

    return await derive_wallet_id()


async def file_claim(
    entry: StoredEntry, counter: int, auth_commit: bytes
) -> bool:
    """Record which queued change was offered, at which counter, and for which transition.

    False if the journal is full, which the caller must treat as "do not offer" -- see
    `mark_offered`.
    """
    from storage import ward as ward_store

    if entry.slot is None:
        # Nothing to file it under. A caller without a slot cannot have read the record, so it
        # cannot be offering one either.
        raise ValueError

    return ward_store.claim_put(
        ward_store.claim_encode(
            await _claim_wallet_id(),
            entry.slot,
            counter,
            auth_commit,
            record_commit(entry.raw),
        )
    )


async def mark_offered(entry: StoredEntry, counter: int, auth_commit: bytes) -> None:
    """Record that this queued change has been handed to a host, keeping it PENDING.

    Two writes, and THE ORDER IS THE POINT. The claim goes first, then the OFFERED flag:

      claim written, flag not  -- a claim for a transition that was never offered. Harmless: the
                                  next adoption finds the record still un-offered, settles nothing,
                                  and retires the claim.
      flag written, claim not  -- the stranded record this journal exists to prevent. The record is
                                  OFFERED so no flush re-offers it, and there is no claim to settle
                                  it by, so it is invisible to `next_unsent` and `count_unsent` and
                                  `remaining` reports zero. Nothing ever asks for it again.

    So a power failure between the two writes must fall on the harmless side, and that is what
    fixes the order rather than taste.

    A FULL JOURNAL REFUSES THE OFFER. Handing the change over without somewhere to record it is the
    stranding case above, arrived at deliberately, so the caller is told instead.

    It stays pending either way: handing the leaf over is not the change taking effect -- the head
    moves when the WM confirms.
    """
    from trezor.wire import DataError

    if not await file_claim(entry, counter, auth_commit):
        raise DataError("WARD: cannot record this change; settle the pending one first")

    await _set_flags(entry, True, True)


async def reconcile_pending(adopted: int, landed_commits: "list | None" = None) -> None:
    """Settle every offered-but-unconfirmed write against the head just adopted.

    This is the ONLY place a queued write stops being queued, and it runs at the same boundary an
    online write commits at: the head moves when the WM confirms a counter, not when a host says it
    stored something. Every outcome is a REWRITE and none is a delete.

    TWO WAYS TO DECIDE WHETHER A CHANGE LANDED, because the two adoption routes carry different
    evidence:

      `landed_commits` given -- the caller verified a CHAIN, so it knows every transition it
                               crossed. A claim landed exactly when its `auth_commit` is among
                               them. That is precise: it separates "the head reached N" from "MY
                               change is what made it N".

      `landed_commits` None  -- `reconcile` adopts by binding a root to an attested mac and folds no
                               links, so there is nothing to match against and the counter is all
                               there is: claimed <= adopted. See the limitation below.

    AND THE RECORD MUST STILL BE THE ONE THAT WAS OFFERED. Slots are reused and a queued value can
    be replaced in place, so the claim's `record_commit` is compared against whatever occupies the
    slot now. A mismatch means the offered generation is gone: the transition is still resolved, but
    this record is not the one it was about, so it is left exactly as it is. Without that check,
    offering A, replacing it with B and then watching A land would clear B -- a change that never
    landed, silently discarded.

      landed, record matches     : both flags go; the record stays as the cached copy of the value
                                   now in the tree.
      not landed, record matches : the OFFERED flag goes and the record stays PENDING, so
                                   `flush_queue` offers it again. Without this a lost or dropped
                                   publication would strand the change forever.
      record does not match      : untouched.

    The claim is retired either way, because its transition's fate is now known. Leaving it would
    let the NEXT adoption settle the same records against a later head.

    Records that were never offered are untouched, and so are other wallets' claims -- the journal
    is scoped by wallet_id, which is what stops one wallet's reconciliation from rewriting another
    wallet's queued records.

    KNOWN LIMITATION, ON THE COUNTER PATH ONLY. "The head reached N" is not quite "my change is what
    made it N": if another device of this wallet advanced the counter first, this clears a record
    whose change did not land, and the value survives only as a cached copy. The divergence itself
    is caught by reconcile's same-counter-different-root check. The chain path above does not have
    this problem, which is the better reason to prefer it.
    """
    from storage import ward as ward_store

    # DRIVEN BY THE JOURNAL, NOT BY ENUMERATION. Every claim in it was filed by THIS wallet, so it
    # is a stricter handle than "records of my wallet" -- and it is the only one a compact record
    # can be reached by, since such a record carries nothing that says whose it is. It also touches
    # exactly the records it offered, and no others.
    wallet_id = await _claim_wallet_id()
    for index, claim in ward_store.claim_list(wallet_id):
        _w, slot, claimed, auth_commit, commit = ward_store.claim_parse(claim)
        record = ward_store.store_read_slot(slot)
        if record is None or record[0] not in (
            ward_store.STORE_VERSION,
            ward_store.STORE_VERSION_COMPACT,
        ):
            # Erased, or replaced by something this build cannot read, since it was offered.
            # Nothing to settle and nothing here may delete -- but the claim is spent.
            ward_store.claim_delete(index)
            continue

        entry = _parse(record, slot=slot)
        if entry.pending and entry.offered and record_commit(record) == commit:
            if landed_commits is not None:
                landed = auth_commit in landed_commits
            else:
                landed = claimed <= adopted
            await _set_flags(entry, not landed, False)

        ward_store.claim_delete(index)
