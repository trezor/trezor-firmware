"""Persistent WARD state, per hidden wallet: root slots, host pins, the offline store, claims.

Key ranges are disjoint so no record is ever read as another kind: roots 1..MAX_WALLETS, service
pin 0x10, app pin 0x11, claims 0x20.., offline records 0x40...

Every slot is keyed by wallet_id (`apps.ward.keys.derive_wallet_id`), so a passphrase switch never
sees another wallet's root or records. When slots or bytes run out the store REFUSES rather than
evicting, and nothing is ever erased implicitly: only a user-confirmed erase or replacement removes
a record. Records are plaintext because `storage.c` already seals each value under a PIN-derived
key with the slot number as AAD; sealing under K_data happens only on export.
"""

from micropython import const

from storage import common

_WALLET_ID_LEN = const(16)
_ROOT_LEN = const(32)
_COUNTER_LEN = const(4)

# root slot: wallet_id(16) || root(32) || counter(4)
MAX_WALLETS = const(8)
_FIRST_KEY = const(1)


def _first_free(n: int, get) -> int | None:
    for i in range(n):
        if get(i) is None:
            return i
    return None


def _slot(index: int) -> bytes | None:
    return common.get(common.APP_WARD, index + _FIRST_KEY)


def _find(wallet_id: bytes) -> "tuple[int, bytes] | None":
    for i in range(MAX_WALLETS):
        rec = _slot(i)
        if rec is not None and rec[:_WALLET_ID_LEN] == wallet_id:
            return i, rec
    return None


def get_root(wallet_id: bytes) -> bytes | None:
    """This wallet's stored root, or None ("cannot verify", never "verified")."""
    found = _find(wallet_id)
    if found is None:
        return None
    root = found[1][_WALLET_ID_LEN : _WALLET_ID_LEN + _ROOT_LEN]
    # An empty tree is stored as EMPTY_ROOT; all-zero only ever means "no root".
    if root == bytes(_ROOT_LEN):
        return None
    return root


def get_counter(wallet_id: bytes) -> int:
    """The anti-rollback floor: the highest counter this wallet has accepted, 0 if unseen."""
    found = _find(wallet_id)
    if found is None:
        return 0
    off = _WALLET_ID_LEN + _ROOT_LEN
    return int.from_bytes(found[1][off : off + _COUNTER_LEN], "big")


def set_root(wallet_id: bytes, root: bytes | None, counter: int = 0) -> bool:
    """Record this wallet's root and counter. False if every slot belongs to another wallet.

    The result is not advisory: a caller that ignores False believes it adopted a head it did not
    store, and an absent root at counter 0 reads as "nothing was ever written".
    """
    if len(wallet_id) != _WALLET_ID_LEN:
        raise ValueError  # wallet_id must be exactly _WALLET_ID_LEN bytes

    found = _find(wallet_id)
    index = found[0] if found is not None else _first_free(MAX_WALLETS, _slot)
    if index is None:
        return False

    common.set(
        common.APP_WARD,
        index + _FIRST_KEY,
        wallet_id
        + (root if root is not None else bytes(_ROOT_LEN))
        + counter.to_bytes(_COUNTER_LEN, "big"),
    )
    return True


# --- host pins ------------------------------------------------------------------------
#
# Pairing admits every paired host; a pin names ONE daemon (service) and ONE app (TOFU). In flash,
# because a binding that dissolved on reboot could be taken over by unplugging the device. Clearing
# a pin touches nothing else; whether to allow the migration is the caller's decision.
_SERVICE_HOST_KEY = const(0x10)
_SERVICE_HOST_KEY_LEN = const(32)
_APP_HOST_KEY = const(0x11)
_APP_HOST_KEY_LEN = const(32)


def get_service_host_key() -> bytes | None:
    """The daemon this device has bound to, or None if none has claimed the role."""
    return common.get(common.APP_WARD, _SERVICE_HOST_KEY)


def set_service_host_key(key: bytes) -> None:
    """Pin the daemon. Refuses a wrong-width key rather than storing a truncated one."""
    if len(key) != _SERVICE_HOST_KEY_LEN:
        raise ValueError("service host key must be 32 bytes")
    common.set(common.APP_WARD, _SERVICE_HOST_KEY, key)


def clear_service_host_key() -> None:
    """Retire the daemon pin, so the next daemon to announce itself may claim the role."""
    common.delete(common.APP_WARD, _SERVICE_HOST_KEY)


def get_app_host_key() -> bytes | None:
    """The app this device has bound to for WARD, or None if none has claimed the role."""
    return common.get(common.APP_WARD, _APP_HOST_KEY)


def set_app_host_key(key: bytes) -> None:
    """Pin the app. Refuses a wrong-width key rather than storing a truncated one."""
    if len(key) != _APP_HOST_KEY_LEN:
        raise ValueError("app host key must be 32 bytes")
    common.set(common.APP_WARD, _APP_HOST_KEY, key)


def clear_app_host_key() -> None:
    """Retire the app pin, so the next app to make a WARD request may claim the role."""
    common.delete(common.APP_WARD, _APP_HOST_KEY)


# --- the offline store ------------------------------------------------------------------
#
# Cached reads and pending writes, one record type, one shared pool across wallets. Bounded by
# slots AND by total bytes (the norcow sector is shared with everything else); either limit reports
# the same "full".
_STORE_FIRST_KEY = const(0x40)
MAX_STORE_ENTRIES = const(20)
MAX_VALUE_LEN = const(1024)  # room for a BIP-388 wallet policy, not just a label
MAX_RECORD_LEN = const(1152)  # a value plus the identity framing around it
MAX_STORE_BYTES = const(6144)

STORE_VERSION = const(3)  # the full form: the identity is in the record
STORE_VERSION_COMPACT = const(4)  # the identity is replaced by a 16-byte hash of it

# The full form tags records with wallet_id[:7]: enough to tell this device's wallets apart, and it
# authorises nothing (storage.c already gates reads on the PIN). The compact form carries no tag --
# its name is a hash over wallet_id -- so `store_list` cannot enumerate it.
_STORE_WALLET_ID_LEN = const(7)

FLAG_PENDING = const(0x01)  # a local write that has not been published yet
FLAG_OFFERED = const(0x02)  # ...and it has been handed to a host this side of a reconcile

# FROZEN HEADER, across every future version: version(1) || wallet_id(7) || identity. A build that
# cannot parse a newer record must still find it to let the user erase it.
_STORE_VERSION_OFF = const(0)
_STORE_ID_OFF = const(1)
STORE_KEY_OFF = const(8)  # where the identity begins
STORE_PREFIX_LEN = const(8)


def store_prefix(wallet_id: bytes, version: int = STORE_VERSION) -> bytes:
    """The fixed header for `version`: version || wallet_id[:7], or just version when compact."""
    if len(wallet_id) != _WALLET_ID_LEN:
        raise ValueError  # wallet_id must be exactly _WALLET_ID_LEN bytes
    if version == STORE_VERSION_COMPACT:
        return bytes([version])
    if version != STORE_VERSION:
        raise ValueError  # only the forms this build knows may be written
    return bytes([version]) + wallet_id[:_STORE_WALLET_ID_LEN]


def store_key_off(version: int) -> int:
    """Where a record's name begins, which is the one thing the two forms disagree about."""
    return 1 if version == STORE_VERSION_COMPACT else STORE_KEY_OFF


def _store_slot(index: int) -> bytes | None:
    return common.get(common.APP_WARD, index + _STORE_FIRST_KEY)


def _store_tag_matches(rec: bytes, wallet_id: bytes) -> bool:
    return rec[_STORE_ID_OFF:STORE_KEY_OFF] == wallet_id[:_STORE_WALLET_ID_LEN]


def _check_wallet_id(wallet_id: bytes) -> None:
    if len(wallet_id) != _WALLET_ID_LEN:
        raise ValueError  # wallet_id must be exactly _WALLET_ID_LEN bytes


def _check_index(index: int) -> None:
    if not 0 <= index < MAX_STORE_ENTRIES:
        raise ValueError  # slot index out of range


def store_find(wallet_id: bytes, candidates: "list[tuple[int, bytes]]") -> int | None:
    """This wallet's slot for any `(version, key)` candidate, or None.

    Matches version, wallet and key at fixed offsets, never the key alone: the same identifier
    under another passphrase is another wallet's entry.
    """
    if len(wallet_id) != _WALLET_ID_LEN or not candidates:
        raise ValueError  # a record is always named by a wallet and at least one key
    for version, key in candidates:
        if not key:
            raise ValueError  # an empty key would match every record of the wallet
    for i in range(MAX_STORE_ENTRIES):
        rec = _store_slot(i)
        if rec is None or len(rec) < 1 + _STORE_WALLET_ID_LEN:
            continue
        for version, key in candidates:
            if rec[_STORE_VERSION_OFF] != version:
                continue
            # a compact name is a hash over wallet_id, so only the full form needs the tag check
            if version == STORE_VERSION and not _store_tag_matches(rec, wallet_id):
                continue
            off = store_key_off(version)
            if rec[off : off + len(key)] == key:
                return i
    return None


def store_get(wallet_id: bytes, candidates: "list[tuple[int, bytes]]") -> bytes | None:
    """The raw record, or None. Raw so "cannot read" never collapses into "no such entry"."""
    index = store_find(wallet_id, candidates)
    if index is None:
        return None
    return _store_slot(index)


def store_bytes_used(exclude_index: "int | None" = None) -> int:
    """Bytes held by every record across ALL wallets, optionally leaving out one slot."""
    total = 0
    for i in range(MAX_STORE_ENTRIES):
        if i == exclude_index:
            continue
        rec = _store_slot(i)
        if rec is not None:
            total += len(rec)
    return total


def store_put(
    wallet_id: bytes,
    version: int,
    key: bytes,
    record: bytes,
    replaces: bytes | None = None,
) -> bool:
    """Write a record, replacing this wallet's one under `key` (or `replaces` in the other form).

    False if full -- no free slot or no room in MAX_STORE_BYTES. Never evicts.
    """
    header = store_prefix(wallet_id, version) + key
    if record[: len(header)] != header:
        raise ValueError  # record header must name the version, wallet and key it is stored under
    if len(record) > MAX_RECORD_LEN:
        raise ValueError  # a record past the cap breaks the capacity guarantee, see MAX_RECORD_LEN

    index = store_find(wallet_id, [(version, key)])
    if index is None and replaces is not None:
        other = (
            STORE_VERSION if version == STORE_VERSION_COMPACT else STORE_VERSION_COMPACT
        )
        index = store_find(wallet_id, [(other, replaces)])
    if index is None:
        index = _first_free(MAX_STORE_ENTRIES, _store_slot)
    if index is None:
        return False

    # a replacement pays only the difference
    if store_bytes_used(exclude_index=index) + len(record) > MAX_STORE_BYTES:
        return False

    common.set(common.APP_WARD, index + _STORE_FIRST_KEY, record)
    return True


def store_delete(wallet_id: bytes, candidates: "list[tuple[int, bytes]]") -> None:
    """Remove this wallet's matching record, if any. The caller must hold the user's consent."""
    index = store_find(wallet_id, candidates)
    if index is None:
        return
    common.delete(common.APP_WARD, index + _STORE_FIRST_KEY)


def store_find_unreadable(wallet_id: bytes) -> int | None:
    """A full-shaped slot of this wallet whose version this build cannot parse, or None.

    Found by the frozen header alone, so a newer record can still be erased on user request.
    """
    _check_wallet_id(wallet_id)
    for i in range(MAX_STORE_ENTRIES):
        rec = _store_slot(i)
        if rec is None or len(rec) < STORE_PREFIX_LEN:
            continue
        if _store_tag_matches(rec, wallet_id) and rec[_STORE_VERSION_OFF] not in (
            STORE_VERSION,
            STORE_VERSION_COMPACT,
        ):
            return i
    return None


def store_delete_slot(index: int) -> None:
    """Remove whatever occupies one slot. Unreadable-record path only; caller holds consent."""
    _check_index(index)
    common.delete(common.APP_WARD, index + _STORE_FIRST_KEY)


def store_read_slot(index: int) -> bytes | None:
    """Whatever occupies one slot, by index."""
    _check_index(index)
    return _store_slot(index)


def store_write_slot(index: int, record: bytes) -> None:
    """Rewrite a slot the caller already owns IN PLACE, same length. For flag flips only."""
    _check_index(index)
    old = _store_slot(index)
    if old is None or len(old) != len(record):
        raise ValueError  # in-place means the same length; anything else goes through store_put
    common.set(common.APP_WARD, index + _STORE_FIRST_KEY, record)


def store_list(wallet_id: bytes) -> "list[tuple[int, bytes]]":
    """Every FULL-form record of THIS wallet as (slot, record); compact records cannot be listed."""
    _check_wallet_id(wallet_id)
    out = []
    for i in range(MAX_STORE_ENTRIES):
        rec = _store_slot(i)
        if rec is None or len(rec) < STORE_PREFIX_LEN:
            continue
        if _store_tag_matches(rec, wallet_id):
            out.append((i, rec))
    return out


# --- the offer claim journal ------------------------------------------------------------
#
# A claim remembers, across power loss, which queued record `flush_queue` offered at which counter,
# so the next adoption can settle it. One per record slot. It names the record GENERATION
# (`record_commit`), so a slot reused or replaced after the offer is never settled by mistake.
_CLAIM_FIRST_KEY = const(0x20)
MAX_CLAIMS = const(MAX_STORE_ENTRIES)
_CLAIM_SLOT_LEN = const(1)
_CLAIM_COUNTER_LEN = const(4)
_CLAIM_AUTH_LEN = const(32)
_CLAIM_COMMIT_LEN = const(32)
# wallet_id(16) || slot(1) || counter(4) || auth_commit(32) || record_commit(32)
CLAIM_LEN = const(
    _WALLET_ID_LEN
    + _CLAIM_SLOT_LEN
    + _CLAIM_COUNTER_LEN
    + _CLAIM_AUTH_LEN
    + _CLAIM_COMMIT_LEN
)


def _claim_slot(index: int) -> bytes | None:
    return common.get(common.APP_WARD, index + _CLAIM_FIRST_KEY)


def claim_encode(
    wallet_id: bytes, slot: int, counter: int, auth_commit: bytes, record_commit: bytes
) -> bytes:
    """The canonical bytes of one claim, under the FULL 16-byte wallet_id."""
    _check_wallet_id(wallet_id)
    if len(auth_commit) != _CLAIM_AUTH_LEN or len(record_commit) != _CLAIM_COMMIT_LEN:
        raise ValueError  # both commitments are fixed width
    if not 0 <= slot < MAX_STORE_ENTRIES:
        raise ValueError  # a claim can only name a record slot that exists
    return (
        wallet_id
        + bytes([slot])
        + counter.to_bytes(_CLAIM_COUNTER_LEN, "big")
        + auth_commit
        + record_commit
    )


def claim_parse(rec: bytes) -> "tuple[bytes, int, int, bytes, bytes]":
    """(wallet_id, slot, counter, auth_commit, record_commit), or raise on a wrong width."""
    if len(rec) != CLAIM_LEN:
        raise ValueError  # a short claim would parse into plausible-looking garbage
    off = _WALLET_ID_LEN
    wallet_id = rec[:off]
    slot = rec[off]
    off += _CLAIM_SLOT_LEN
    counter = int.from_bytes(rec[off : off + _CLAIM_COUNTER_LEN], "big")
    off += _CLAIM_COUNTER_LEN
    auth_commit = rec[off : off + _CLAIM_AUTH_LEN]
    off += _CLAIM_AUTH_LEN
    return wallet_id, slot, counter, auth_commit, rec[off:]


def claim_list(wallet_id: bytes) -> "list[tuple[int, bytes]]":
    """This wallet's well-formed claims as (index, record) pairs."""
    _check_wallet_id(wallet_id)
    out = []
    for i in range(MAX_CLAIMS):
        rec = claim_read(i)
        if rec is not None and rec[:_WALLET_ID_LEN] == wallet_id:
            out.append((i, rec))
    return out


def claim_find(wallet_id: bytes, slot: int) -> int | None:
    """The index holding this wallet's claim for this record slot, or None."""
    for i, rec in claim_list(wallet_id):
        if rec[_WALLET_ID_LEN] == slot:
            return i
    return None


def claim_put(rec: bytes) -> bool:
    """File a claim, replacing this wallet's one for the same slot. False if the journal is full."""
    wallet_id, slot, _c, _a, _r = claim_parse(rec)
    index = claim_find(wallet_id, slot)
    if index is None:
        index = _first_free(MAX_CLAIMS, _claim_slot)
    if index is None:
        return False
    common.set(common.APP_WARD, index + _CLAIM_FIRST_KEY, rec)
    return True


def claims_fit(wallet_id: bytes, slots: "list[int]") -> bool:
    """Would a claim for every one of `slots` fit? Asked before a batch files any of them."""
    needed = sum(1 for slot in slots if claim_find(wallet_id, slot) is None)
    free = sum(1 for i in range(MAX_CLAIMS) if _claim_slot(i) is None)
    return needed <= free


def claim_read(index: int) -> bytes | None:
    """One claim by index, or None if the slot is empty or unreadable."""
    rec = _claim_slot(index)
    if rec is None or len(rec) != CLAIM_LEN:
        return None
    return rec


def claim_delete(index: int) -> None:
    """Retire a claim. Called once its outcome has been decided, and only then."""
    common.delete(common.APP_WARD, index + _CLAIM_FIRST_KEY)
