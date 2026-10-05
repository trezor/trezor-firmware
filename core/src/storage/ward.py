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


class _Range:
    """`n` consecutive keys of APP_WARD from `first`, addressed by index."""

    def __init__(self, first: int, n: int) -> None:
        self.first = first
        self.n = n

    def get(self, i: int) -> bytes | None:
        return common.get(common.APP_WARD, self.first + i)

    def set(self, i: int, value: bytes) -> None:
        common.set(common.APP_WARD, self.first + i, value)

    def delete(self, i: int) -> None:
        common.delete(common.APP_WARD, self.first + i)

    def items(self) -> "list[tuple[int, bytes]]":
        """Every occupied index with its value, in index order."""
        out = []
        for i in range(self.n):
            rec = self.get(i)
            if rec is not None:
                out.append((i, rec))
        return out

    def free_count(self) -> int:
        return sum(1 for i in range(self.n) if self.get(i) is None)

    def first_free(self) -> int | None:
        for i in range(self.n):
            if self.get(i) is None:
                return i
        return None


def _check_wallet_id(wallet_id: bytes) -> None:
    if len(wallet_id) != _WALLET_ID_LEN:
        raise ValueError  # wallet_id must be exactly _WALLET_ID_LEN bytes


# --- root slots: wallet_id(16) || root(32) || counter(4) ------------------------------
MAX_WALLETS = const(8)
_ROOTS = _Range(1, MAX_WALLETS)


def _find(wallet_id: bytes) -> "tuple[int, bytes] | None":
    for i, rec in _ROOTS.items():
        if rec[:_WALLET_ID_LEN] == wallet_id:
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
    _check_wallet_id(wallet_id)

    found = _find(wallet_id)
    index = found[0] if found is not None else _ROOTS.first_free()
    if index is None:
        return False

    _ROOTS.set(
        index,
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
_APP_HOST_KEY = const(0x11)


def _pin_set(key: int, host_key: bytes, role: str) -> None:
    # refuses a wrong-width key rather than storing a truncated one
    if len(host_key) != 32:
        raise ValueError(role + " host key must be 32 bytes")
    common.set(common.APP_WARD, key, host_key)


def get_service_host_key() -> bytes | None:
    """The daemon this device has bound to, or None if none has claimed the role."""
    return common.get(common.APP_WARD, _SERVICE_HOST_KEY)


def set_service_host_key(key: bytes) -> None:
    _pin_set(_SERVICE_HOST_KEY, key, "service")


def clear_service_host_key() -> None:
    """Retire the daemon pin, so the next daemon to announce itself may claim the role."""
    common.delete(common.APP_WARD, _SERVICE_HOST_KEY)


def get_app_host_key() -> bytes | None:
    """The app this device has bound to for WARD, or None if none has claimed the role."""
    return common.get(common.APP_WARD, _APP_HOST_KEY)


def set_app_host_key(key: bytes) -> None:
    _pin_set(_APP_HOST_KEY, key, "app")


def clear_app_host_key() -> None:
    """Retire the app pin, so the next app to make a WARD request may claim the role."""
    common.delete(common.APP_WARD, _APP_HOST_KEY)


# --- the offline store ------------------------------------------------------------------
#
# Cached reads and pending writes, one record type, one shared pool across wallets. Bounded by
# slots AND by total bytes (the norcow sector is shared with everything else); either limit reports
# the same "full".
MAX_STORE_ENTRIES = const(20)
_STORE = _Range(0x40, MAX_STORE_ENTRIES)
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
_STORE_ID_OFF = const(1)
STORE_KEY_OFF = const(8)  # where the identity begins
STORE_PREFIX_LEN = const(8)


def store_prefix(wallet_id: bytes, version: int = STORE_VERSION) -> bytes:
    """The fixed header for `version`: version || wallet_id[:7], or just version when compact."""
    _check_wallet_id(wallet_id)
    if version == STORE_VERSION_COMPACT:
        return bytes([version])
    if version != STORE_VERSION:
        raise ValueError  # only the forms this build knows may be written
    return bytes([version]) + wallet_id[:_STORE_WALLET_ID_LEN]


def store_key_off(version: int) -> int:
    """Where a record's name begins, which is the one thing the two forms disagree about."""
    return 1 if version == STORE_VERSION_COMPACT else STORE_KEY_OFF


def _check_index(index: int) -> None:
    if not 0 <= index < MAX_STORE_ENTRIES:
        raise ValueError  # slot index out of range


def _has_tag(rec: bytes, wallet_id: bytes) -> bool:
    return rec[_STORE_ID_OFF:STORE_KEY_OFF] == wallet_id[:_STORE_WALLET_ID_LEN]


def _headed() -> "list[tuple[int, bytes]]":
    """Every slot long enough to carry the frozen header."""
    return [(i, rec) for i, rec in _STORE.items() if len(rec) >= STORE_PREFIX_LEN]


def store_find(wallet_id: bytes, candidates: "list[tuple[int, bytes]]") -> int | None:
    """This wallet's slot for any `(version, key)` candidate, or None.

    Matches version, wallet and key at fixed offsets, never the key alone: the same identifier
    under another passphrase is another wallet's entry.
    """
    if len(wallet_id) != _WALLET_ID_LEN or not candidates:
        raise ValueError  # a record is always named by a wallet and at least one key
    for _version, key in candidates:
        if not key:
            raise ValueError  # an empty key would match every record of the wallet
    for i, rec in _headed():
        for version, key in candidates:
            if rec[0] != version:
                continue
            # a compact name is a hash over wallet_id, so only the full form needs the tag check
            if version == STORE_VERSION and not _has_tag(rec, wallet_id):
                continue
            off = store_key_off(version)
            if rec[off : off + len(key)] == key:
                return i
    return None


def store_get(wallet_id: bytes, candidates: "list[tuple[int, bytes]]") -> bytes | None:
    """The raw record, or None. Raw so "cannot read" never collapses into "no such entry"."""
    index = store_find(wallet_id, candidates)
    return None if index is None else _STORE.get(index)


def store_bytes_used(exclude_index: "int | None" = None) -> int:
    """Bytes held by every record across ALL wallets, optionally leaving out one slot."""
    return sum(len(rec) for i, rec in _STORE.items() if i != exclude_index)


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
        index = _STORE.first_free()
    if index is None:
        return False

    # a replacement pays only the difference
    if store_bytes_used(exclude_index=index) + len(record) > MAX_STORE_BYTES:
        return False

    _STORE.set(index, record)
    return True


def store_delete(wallet_id: bytes, candidates: "list[tuple[int, bytes]]") -> None:
    """Remove this wallet's matching record, if any. The caller must hold the user's consent."""
    index = store_find(wallet_id, candidates)
    if index is not None:
        _STORE.delete(index)


def store_find_unreadable(wallet_id: bytes) -> int | None:
    """A full-shaped slot of this wallet whose version this build cannot parse, or None.

    Found by the frozen header alone, so a newer record can still be erased on user request.
    """
    for i, rec in store_list(wallet_id):
        if rec[0] not in (STORE_VERSION, STORE_VERSION_COMPACT):
            return i
    return None


def store_delete_slot(index: int) -> None:
    """Remove whatever occupies one slot. Unreadable-record path only; caller holds consent."""
    _check_index(index)
    _STORE.delete(index)


def store_read_slot(index: int) -> bytes | None:
    """Whatever occupies one slot, by index."""
    _check_index(index)
    return _STORE.get(index)


def store_write_slot(index: int, record: bytes) -> None:
    """Rewrite a slot the caller already owns IN PLACE, same length. For flag flips only."""
    _check_index(index)
    old = _STORE.get(index)
    if old is None or len(old) != len(record):
        raise ValueError  # in-place means the same length; anything else goes through store_put
    _STORE.set(index, record)


def store_list(wallet_id: bytes) -> "list[tuple[int, bytes]]":
    """Every full-header slot of THIS wallet as (slot, record), whatever its version; compact
    records carry no tag and cannot be listed."""
    _check_wallet_id(wallet_id)
    return [(i, rec) for i, rec in _headed() if _has_tag(rec, wallet_id)]


# --- the offer claim journal ------------------------------------------------------------
#
# A claim remembers, across power loss, which queued record `flush_queue` offered at which counter,
# so the next adoption can settle it. One per record slot. It names the record GENERATION
# (`record_commit`), so a slot reused or replaced after the offer is never settled by mistake.
#
# wallet_id(16) || slot(1) || counter(4) || auth_commit(32) || record_commit(32)
MAX_CLAIMS = const(MAX_STORE_ENTRIES)
_CLAIMS = _Range(0x20, MAX_CLAIMS)
_CLAIM_SLOT_OFF = const(16)
_CLAIM_COUNTER_OFF = const(17)
_CLAIM_AUTH_OFF = const(21)
_CLAIM_COMMIT_OFF = const(53)
CLAIM_LEN = const(85)


def claim_encode(
    wallet_id: bytes, slot: int, counter: int, auth_commit: bytes, record_commit: bytes
) -> bytes:
    """The canonical bytes of one claim, under the FULL 16-byte wallet_id."""
    _check_wallet_id(wallet_id)
    if len(auth_commit) != 32 or len(record_commit) != 32:
        raise ValueError  # both commitments are fixed width
    if not 0 <= slot < MAX_STORE_ENTRIES:
        raise ValueError  # a claim can only name a record slot that exists
    return (
        wallet_id
        + bytes([slot])
        + counter.to_bytes(_COUNTER_LEN, "big")
        + auth_commit
        + record_commit
    )


def claim_parse(rec: bytes) -> "tuple[bytes, int, int, bytes, bytes]":
    """(wallet_id, slot, counter, auth_commit, record_commit), or raise on a wrong width."""
    if len(rec) != CLAIM_LEN:
        raise ValueError  # a short claim would parse into plausible-looking garbage
    return (
        rec[:_CLAIM_SLOT_OFF],
        rec[_CLAIM_SLOT_OFF],
        int.from_bytes(rec[_CLAIM_COUNTER_OFF:_CLAIM_AUTH_OFF], "big"),
        rec[_CLAIM_AUTH_OFF:_CLAIM_COMMIT_OFF],
        rec[_CLAIM_COMMIT_OFF:],
    )


def claim_read(index: int) -> bytes | None:
    """One claim by index, or None if the slot is empty or unreadable."""
    rec = _CLAIMS.get(index)
    return rec if rec is not None and len(rec) == CLAIM_LEN else None


def claim_list(wallet_id: bytes) -> "list[tuple[int, bytes]]":
    """This wallet's well-formed claims as (index, record) pairs."""
    _check_wallet_id(wallet_id)
    return [
        (i, rec)
        for i, rec in _CLAIMS.items()
        if len(rec) == CLAIM_LEN and rec[:_WALLET_ID_LEN] == wallet_id
    ]


def claim_find(wallet_id: bytes, slot: int) -> int | None:
    """The index holding this wallet's claim for this record slot, or None."""
    for i, rec in claim_list(wallet_id):
        if rec[_CLAIM_SLOT_OFF] == slot:
            return i
    return None


def claim_put(rec: bytes) -> bool:
    """File a claim, replacing this wallet's one for the same slot. False if the journal is full."""
    wallet_id, slot, _c, _a, _r = claim_parse(rec)
    index = claim_find(wallet_id, slot)
    if index is None:
        index = _CLAIMS.first_free()
    if index is None:
        return False
    _CLAIMS.set(index, rec)
    return True


def claims_fit(wallet_id: bytes, slots: "list[int]") -> bool:
    """Would a claim for every one of `slots` fit? Asked before a batch files any of them."""
    needed = sum(1 for slot in slots if claim_find(wallet_id, slot) is None)
    return needed <= _CLAIMS.free_count()


def claim_delete(index: int) -> None:
    """Retire a claim. Called once its outcome has been decided, and only then."""
    _CLAIMS.delete(index)
