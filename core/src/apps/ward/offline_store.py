"""The device's own entries: pinned copies of leaves, and writes it could not publish.

One record type for both roles; `FLAG_PENDING` says which, and only `reconcile_pending` clears it.
Records are named by identity (full form) or by `keys.wallet_entry`, a hash of it (compact form);
every caller here knows the identity, so both names are tried. Compact records carry no wallet tag,
so they are reachable by name or claimed slot, never by enumeration.

`get` answers MISS, VALID or CORRUPT and never collapses "cannot read" into "absent". Nothing here
ever deletes except `erase`/`erase_unreadable`, whose callers hold the user's confirmation.
"""

from micropython import const

MISS = const(0)
VALID = const(1)
CORRUPT = const(2)


class StoredEntry:
    """One record, opened. `slot`/`raw` let flag flips rewrite in place without an identity."""

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
        # a compact record's identity fields came from the caller, not the record
        self.compact = compact
        self.slot = slot
        self.raw = raw


def _flags(pending: bool, offered: bool) -> int:
    from storage.ward import FLAG_OFFERED, FLAG_PENDING

    return (FLAG_PENDING if pending else 0) | (FLAG_OFFERED if offered else 0)


def _known(record: bytes) -> bool:
    from storage.ward import STORE_VERSION, STORE_VERSION_COMPACT

    return record[0] in (STORE_VERSION, STORE_VERSION_COMPACT)


def identity_block(key_type: str, app_id: str, identifier: bytes) -> bytes:
    """The canonical, length-prefixed bytes a record is found by:

    len8(key_type) || key_type || len8(app_id) || app_id || len16(identifier) || identifier
    """
    from .codec import lp

    too_long = "WARD: key_type or app_id too long to store"
    return (
        lp(1, key_type.encode(), too_long)
        + lp(1, app_id.encode(), too_long)
        + lp(2, identifier, "WARD: identifier too long to store")
    )


async def _candidates(
    key_type: str, app_id: str, identifier: bytes
) -> "list[tuple[int, bytes]]":
    """Both names an entry can be stored under, full form first."""
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
    """The canonical bytes of one record -- the only encoder, so an unchanged refresh is a no-op.

    prefix || (identity_block | wallet_entry(16)) || flags(1) || len16(value) || value
    """
    from storage.ward import STORE_VERSION, STORE_VERSION_COMPACT, store_prefix

    from .codec import lp
    from .keys import wallet_entry

    # the value is checked before the name, as it always was
    value_field = lp(2, value, "WARD: value too long to store")
    if compact:
        version = STORE_VERSION_COMPACT
        name = wallet_entry(wallet_id, app_id, identifier, key_type)
    else:
        version = STORE_VERSION
        name = identity_block(key_type, app_id, identifier)

    return (
        store_prefix(wallet_id, version) + name + bytes([_flags(pending, offered)]) + value_field
    )


def _read_name(record: bytes) -> tuple:
    """A Reader positioned at the flags byte, and the record's identity (None when compact)."""
    from storage.ward import STORE_VERSION_COMPACT, store_key_off

    from .codec import Reader
    from .keys import WALLET_ENTRY_LEN

    r = Reader(record, store_key_off(record[0]))
    if record[0] == STORE_VERSION_COMPACT:
        r.take(WALLET_ENTRY_LEN)
        return r, None
    return r, (r.lp(1).decode(), r.lp(1).decode(), r.lp(2))


def _parse(
    record: bytes,
    key_type: str | None = None,
    app_id: str | None = None,
    identifier: bytes | None = None,
    slot: "int | None" = None,
) -> StoredEntry:
    """Bytes back to a StoredEntry, or raise. A compact record takes the caller's identity (empty
    when enumerating)."""
    from storage.ward import FLAG_OFFERED, FLAG_PENDING
    from trezor.wire import DataError

    r, name = _read_name(record)
    if name is not None:
        key_type, app_id, identifier = name
    flags = r.uint(1)
    value = r.lp(2)
    if not r.done():
        raise DataError("WARD: trailing bytes in record")

    return StoredEntry(
        key_type=key_type if key_type is not None else "",
        app_id=app_id if app_id is not None else "",
        identifier=identifier if identifier is not None else b"",
        value=value,
        pending=bool(flags & FLAG_PENDING),
        offered=bool(flags & FLAG_OFFERED),
        compact=name is None,
        slot=slot,
        raw=record,
    )


def _flags_off(record: bytes) -> int:
    """Where the flags byte sits, whichever form the record is in."""
    return _read_name(record)[0].off


def record_commit(record: bytes) -> bytes:
    """A fingerprint of a record GENERATION, flags normalised out (they move while a claim is open).

    Lets a claim refuse to settle a slot that was reused or replaced after the offer.
    """
    from trezor.crypto.hashlib import sha256

    off = _flags_off(record)
    h = sha256(b"WARD RECORD v1")
    h.update(record[:off])
    h.update(b"\x00")
    h.update(record[off + 1 :])
    return h.digest()


async def _set_flags(entry: StoredEntry, pending: bool, offered: bool) -> None:
    """Rewrite one record's flags in place, in whatever form it is stored."""
    from storage import ward as ward_store

    if entry.slot is None:
        raise ValueError  # only a record that came from `list_entries` can be flipped

    off = _flags_off(entry.raw)
    ward_store.store_write_slot(
        entry.slot,
        entry.raw[:off] + bytes([_flags(pending, offered)]) + entry.raw[off + 1 :],
    )


async def get(
    key_type: str, app_id: str, identifier: bytes
) -> "tuple[int, StoredEntry | None]":
    """(status, entry). CORRUPT never degrades to MISS, and nothing here ever deletes."""
    from storage import ward as ward_store

    from .keys import derive_wallet_id

    wallet_id = await derive_wallet_id()
    slot = ward_store.store_find(
        wallet_id, await _candidates(key_type, app_id, identifier)
    )
    record = None if slot is None else ward_store.store_read_slot(slot)

    if record is None:
        # an unreadable record may be this entry from a newer build: refuse rather than invite
        # an overwrite
        if ward_store.store_find_unreadable(wallet_id) is not None:
            return CORRUPT, None
        return MISS, None

    if not _known(record):
        return CORRUPT, None

    try:
        return VALID, _parse(record, key_type, app_id, identifier, slot)
    except Exception:
        return CORRUPT, None


def _sized_record(
    wallet_id: bytes,
    key_type: str,
    app_id: str,
    identifier: bytes,
    value: bytes,
    pending: bool,
    offered: bool = False,
    compact: bool = False,
) -> bytes:
    """`encode_record`, refusing a value or a whole record past the store's caps."""
    from storage import ward as ward_store
    from trezor.wire import DataError

    if len(value) > ward_store.MAX_VALUE_LEN:
        raise DataError("WARD: value too large to keep offline")
    record = encode_record(
        wallet_id, key_type, app_id, identifier, value, pending, offered, compact
    )
    # the identity framing counts too
    if len(record) > ward_store.MAX_RECORD_LEN:
        raise DataError("WARD: entry too large to keep offline")
    return record


def ensure_storable(
    key_type: str, app_id: str, identifier: bytes, value: bytes
) -> None:
    """Raise unless this entry would fit, WITHOUT writing -- so a screen is never shown for
    something that cannot then be stored."""
    _sized_record(bytes(16), key_type, app_id, identifier, value, False)


async def put(
    key_type: str,
    app_id: str,
    identifier: bytes,
    value: bytes,
    pending: bool,
    offered: bool = False,
    compact: bool = False,
) -> None:
    """Write a record, taking over the slot of the same entry in the other form. Raises when the
    store is full -- it never makes room."""
    from storage import ward as ward_store
    from trezor.wire import DataError

    from .keys import derive_wallet_id

    wallet_id = await derive_wallet_id()
    record = _sized_record(
        wallet_id, key_type, app_id, identifier, value, pending, offered, compact
    )
    full, short = await _candidates(key_type, app_id, identifier)
    version, name = short if compact else full
    other = full[1] if compact else short[1]
    if not ward_store.store_put(wallet_id, version, name, record, replaces=other):
        raise DataError("WARD: offline store is full; erase an entry first")


async def erase(key_type: str, app_id: str, identifier: bytes) -> None:
    """Remove a record. THE CALLER MUST ALREADY HOLD THE USER'S CONFIRMATION."""
    from storage import ward as ward_store

    from .keys import derive_wallet_id

    ward_store.store_delete(
        await derive_wallet_id(), await _candidates(key_type, app_id, identifier)
    )


async def erase_unreadable() -> bool:
    """Remove one record this build cannot parse, if any. True if something went. The caller must
    already hold the user's confirmation."""
    from storage import ward as ward_store

    from .keys import derive_wallet_id

    index = ward_store.store_find_unreadable(await derive_wallet_id())
    if index is None:
        return False
    ward_store.store_delete_slot(index)
    return True


async def list_entries() -> "list[StoredEntry]":
    """Every readable full-form record of the ACTIVE wallet, in slot order; unreadable ones are
    skipped, never deleted."""
    from storage import ward as ward_store

    from .keys import derive_wallet_id

    out = []
    for slot, record in ward_store.store_list(await derive_wallet_id()):
        if not _known(record):
            continue
        try:
            out.append(_parse(record, slot=slot))
        except Exception:
            continue
    return out


# A pending record is either queued (not offered: what `flush_queue` takes) or handed to a host
# and awaiting the WM (offered). Only the first is offered again; the second resolves at the next
# adoption, in `reconcile_pending`. Compact records are publishable only by name, so neither
# function below sees them.


async def _unsent() -> "list[StoredEntry]":
    return [e for e in await list_entries() if e.pending and not e.offered]


async def next_unsent() -> "StoredEntry | None":
    """The oldest queued write not yet handed over, publishable unprompted."""
    unsent = await _unsent()
    return unsent[0] if unsent else None


async def count_unsent() -> int:
    """How many queued writes are waiting and publishable unprompted -- the `remaining` figure."""
    return len(await _unsent())


async def file_claim(
    entry: StoredEntry, counter: int, auth_commit: bytes
) -> bool:
    """Journal which record generation was offered, at which counter, for which transition.
    False if the journal is full."""
    from storage import ward as ward_store

    from .keys import derive_wallet_id

    if entry.slot is None:
        raise ValueError

    return ward_store.claim_put(
        ward_store.claim_encode(
            await derive_wallet_id(),
            entry.slot,
            counter,
            auth_commit,
            record_commit(entry.raw),
        )
    )


async def mark_offered(entry: StoredEntry, counter: int, auth_commit: bytes) -> None:
    """Record that this queued change was handed to a host, keeping it PENDING.

    CLAIM FIRST, THEN THE FLAG: a power cut between them leaves a harmless unused claim, never an
    OFFERED record with no claim (invisible to every flush, stranded forever). A full journal
    refuses the offer for the same reason.
    """
    from trezor.wire import DataError

    if not await file_claim(entry, counter, auth_commit):
        raise DataError("WARD: cannot record this change; settle the pending one first")

    await _set_flags(entry, True, True)


async def _claim_produced(
    claimed: int, adopted: int, adopted_root: bytes | None, auth_commit: bytes
) -> bool:
    """Did THIS claim's single-step transition produce the adopted head?

    True only if the adopted counter is the claimed one, our head is still the claim's from-state,
    and the authorisation re-derives over (from-state -> adopted head). Anything else -- including
    any batch claim -- is "cannot tell", which settles as not landed and is offered again.
    """
    if adopted_root is None or claimed != adopted:
        return False

    from .cas import verify_auth_commit
    from .keys import derive_k_auth, derive_ward_id
    from .root import get_counter, get_root

    if await get_counter() != claimed - 1:
        return False

    return verify_auth_commit(
        await derive_k_auth(),
        await derive_ward_id(),
        claimed - 1,
        await get_root(),
        claimed,
        adopted_root,
        auth_commit,
    )


async def reconcile_pending(
    adopted: int, adopted_root: bytes | None, landed_commits: "list | None" = None
) -> None:
    """Settle every claim of this wallet against the head just adopted, then retire it.

    Landed means the claim's `auth_commit` is in `landed_commits` (the transitions the caller
    verified), or -- without that list -- `_claim_produced`. A counter comparison is NOT enough:
    another device can reach the same counter with a different change.

      landed, record unchanged      : both flags cleared; it stays as the cached copy.
      not landed, record unchanged  : OFFERED cleared, so `flush_queue` offers it again.
      record replaced/erased since  : untouched.

    Driven by the journal, so it reaches compact records and touches nothing it did not offer.
    """
    from storage import ward as ward_store

    from .keys import derive_wallet_id

    for index, claim in ward_store.claim_list(await derive_wallet_id()):
        _w, slot, claimed, auth_commit, commit = ward_store.claim_parse(claim)
        record = ward_store.store_read_slot(slot)
        if record is None or not _known(record):
            ward_store.claim_delete(index)
            continue

        entry = _parse(record, slot=slot)
        if entry.pending and entry.offered and record_commit(record) == commit:
            if landed_commits is not None:
                landed = auth_commit in landed_commits
            else:
                landed = await _claim_produced(claimed, adopted, adopted_root, auth_commit)
            await _set_flags(entry, not landed, False)

        ward_store.claim_delete(index)


# --- shared by the offline-store handlers ------------------------------------------------

UNREADABLE = "An offline copy that cannot be read."


def existing_value(status: int, entry: "StoredEntry | None") -> "tuple[str, bool] | None":
    """How an existing record shows on a screen: `(text, is_data)`, or None when there is none."""
    from .common import display_bytes

    if status == VALID and entry is not None:
        return display_bytes(entry.value), True
    if status == CORRUPT:
        return UNREADABLE, False
    return None


async def lookup(msg) -> tuple:
    """`(app_id, identifier, key_type, status, entry)` for a request naming an entry. The key_type
    is the device's own, so a host cannot aim at another key space."""
    from .common import require_key
    from .keys import ENTRY_TYPE_ADDRESS

    app_id, identifier = require_key(msg.app_id, msg.identifier)
    status, entry = await get(ENTRY_TYPE_ADDRESS, app_id, identifier)
    return app_id, identifier, ENTRY_TYPE_ADDRESS, status, entry
