"""Persistent WARD state: the trie root, one per hidden wallet.

The root has to outlive a session. A device that forgets it on reboot verifies nothing
until the next write, and "nothing is checked" is the failure direction that matters --
it looks like ordinary operation.

ONE ROOT PER WALLET, not per device. K_path is derived from the passphrase-dependent seed,
so each hidden wallet has its own trie and therefore its own root. A single shared slot
would hand whichever wallet wrote last a root belonging to another, and every proof would
fail -- so slots are keyed by a wallet_id derived from the same seed (see
`apps.ward.keys.derive_wallet_id`), which identifies the wallet without revealing it.

WHEN THE SLOTS RUN OUT the device does NOT evict an existing wallet. Evicting would
silently strip rollback protection from a wallet the user still has, and they would have no
way to notice; refusing instead degrades only the wallet being introduced right now, which
operates session-only and keeps saying so on screen. Fewer wallets protected, none
silently weakened.

Each slot carries the root and the anti-rollback counter -- 52 bytes, wallet_id(16) +
root(32) + counter(4). A root alone does not identify a moment, since roots repeat whenever
contents repeat, so an old signature naming today's root would be replayable
(ward-design.md 2.4, 8.2 -- bind on the counter, not the root).

Two fields that used to be here are gone. The last attested TIME was never an independent
signal: anti-replay is the counter's job and a malicious WM lies about the clock freely. The
last attested COUNTER became redundant once writes stopped committing -- every stored counter
now arrives from an attestation, so it and the head counter are the same number.

POSTPONED, DELIBERATELY: dropping the ROOT too, which would reach 20 bytes and roughly
two-and-a-half times the hidden wallets. It is derivable -- a sync round re-establishes it
from the WM's attestation plus a root the host supplies, since the mac binds the two and only
a seed-holding device can compute one -- so nothing here is a sole surviving copy.

What stopped it is the cost of recovering it EVERY SESSION rather than the difficulty of
recovering it at all. Every operation reads the root, plain reads included, so with it out of
flash it would live in the session cache and each reconnect would need a WM round before an
address could be shown. That trades working offline reads for wallet capacity, which is a
product decision rather than a technical one.

Two things that used to block it no longer do: the same-counter fork check no longer depends
on a stored root, because commit-on-WM-confirmation means no device can hold an unconfirmed
head at all; and the sequencing worry -- that dropping the root before that change would ship
a brick -- is moot now that it has landed. Reads already fail closed.

Two things still need care if it is ever done. `rollback` mints its REVERT authorisation over
the device's CURRENT head, so with no persisted root it needs a sync round first. And the host
must be able to supply that root from its own link log even when it cannot reconstruct the
tree -- which is the same requirement `rollback` already imposes, and which the host model
satisfies (`WardTrie.links`).

THE OFFLINE STORE: NOW HERE, IN FLASH. It holds two things that look different and are the
same record: CACHED READS -- leaves the device authenticated and the user pinned -- and PENDING
WRITES, changes made with no host able to take them. Both are entries this wallet owns, keyed
the same way and subject to the same erase rule, so splitting them into two stores would have
meant two capacity budgets, two lookup paths and two chances to key one of them wrong.

It lives here rather than in EVOLU because the case that forced it cannot reach EVOLU: a host
that does not speak WARD never sends `WardSync`, cannot answer `WardEntryRequest`, and has no
replica to consult. Serving that host means serving it from this device.

KEYED BY wallet_id AND IDENTITY, never by the keyed path. A passphrase switch must not show one
wallet's entries to another, nor apply one wallet's queued write under another's keys, so every
lookup matches on wallet_id first and nothing is ever found by identity alone.

THE KEYED PATH IS NOT STORED HERE AT ALL. `entry_key` is where a leaf sits in the TRIE, and it is
assigned when a change is published -- a queued change has not been. Keeping it in a record would
have meant storing a derived value that a pending record has no business claiming, and then keeping
it in step with the identity it was derived from. It is derived instead, from the identity, at the
one moment it is needed: publication.

RECORDS ARE PLAINTEXT, and that is a decision with a citation rather than an omission.
`storage.c` already encrypts every protected value with ChaCha20-Poly1305 under a PIN-derived
key, with THE STORAGE SLOT NUMBER AS AAD, on top of a global authentication sum across all keys;
a tag mismatch calls `handle_fault()`. So a record already cannot be read without the PIN, moved
between slots, or silently corrupted -- and re-sealing it under K_data would buy a second copy of
protections that are already there, at the cost of a nonce, a tag and AEAD bucket padding that
would multiply a forty-byte address several times over. Sealing happens on EXPORT, where the
data leaves the device and storage.c stops covering it, and nowhere else.

What plaintext genuinely gives up: K_data is passphrase-derived and the storage key is not, so
nothing cryptographically binds a record to the hidden wallet that wrote it. wallet_id is a field
inside the authenticated record and every lookup matches on it, so wallets still cannot bleed
into each other; the residual gap needs an attacker holding the PIN, who owns the device anyway.

WHEN THE SLOTS RUN OUT, as with wallets above, the device REFUSES rather than evicting. Here the
reason is sharper: an evicted record is either a value the user chose to keep or a change they
confirmed and that has not been published yet. Neither may vanish to make room. See the erase
rule below.

NOTHING IS EVER ERASED IMPLICITLY. No LRU, no TTL, no clean-up on boot, on wallet switch, on root
update, or on pressure. A record may become stale, superseded, incompatible with a newer format,
or unreadable -- none of those authorises removing it. Only a user-confirmed erase or replacement
takes bytes out of flash. This is the invariant the whole store is built to hold:

    head/root:      authenticated global state
    offline store:  local copies and local intents
    advancing or changing the head must NEVER implicitly erase a record

A pinned entry that is out of date is a solvable problem; an entry that disappeared because the
tree moved is a lost one, and the user has no way to notice it happened.

STILL TRUE, AND STILL UNSOLVED. A queued intent is an INTENT, not a transition: a device with no
host cannot pull, so it cannot prove current state and cannot derive a root. An intent formed
against root R is not applicable to R' -- its proof material and derived root are relative to R --
so publishing means RE-DERIVING each one against current state, which is what `flush_queue` does
and is mandatory machinery rather than an optimisation.

KNOWN AND ACCEPTED: ATOMICITY AND CONSENT TRANSFER. A queued batch has no transaction to apply
under -- Evolu's CRDT offers none -- so partial application can leave a state the user never
approved; publishing ONE intent per round-trip bounds the damage without making the batch atomic.
And when another device integrates intents, either it applies them silently, so the user never
learns, or it re-confirms what was already approved once. Both are to be resolved by `rollback`
when they go wrong, which is one more reason that path is load-bearing rather than an escape
hatch (see `apps/ward/rollback.py`).

DELETES ARE NOT QUEUED. Deleting offline means erasing the LOCAL record, user-confirmed -- it does
not remove anything from WARD. A queued logical delete would need the sealed tombstone and the
K_auth intent MAC described in `delete_entry.py`, because today's empty-part delete leaf is
plaintext and any host can construct one for any entry_key; without both, uploading queued deletes
lets a host delete anything. `WardDeleteEntry` therefore requires a connection.
"""

from micropython import const

from storage import common

_WALLET_ID_LEN = const(16)
_ROOT_LEN = const(32)
_COUNTER_LEN = const(4)

# 8 wallets at 52 bytes each. Raising this costs flash and nothing else.
MAX_WALLETS = const(8)
_FIRST_KEY = const(1)


def _slot(index: int) -> bytes | None:
    return common.get(common.APP_WARD, index + _FIRST_KEY)


def _find(wallet_id: bytes) -> int | None:
    for i in range(MAX_WALLETS):
        rec = _slot(i)
        if rec is not None and rec[:_WALLET_ID_LEN] == wallet_id:
            return i
    return None


def get_root(wallet_id: bytes) -> bytes | None:
    """This wallet's stored root, or None if it has none.

    None means "cannot verify", never "verified".
    """
    index = _find(wallet_id)
    if index is None:
        return None
    rec = _slot(index)
    assert rec is not None
    root = rec[_WALLET_ID_LEN : _WALLET_ID_LEN + _ROOT_LEN]
    # All-zero means the slot was written without a root, which no current caller does --
    # an EMPTY TREE is stored as EMPTY_ROOT, a real hash, precisely so that it is not this
    # state. Kept as a defensive floor: an unreadable record must read as "cannot verify".
    if root == bytes(_ROOT_LEN):
        return None
    return root


def get_counter(wallet_id: bytes) -> int:
    """The anti-rollback floor: the highest counter this wallet has accepted.

    Zero for a wallet the device has never seen, which is also the state in which no
    counter check can help -- there is nothing yet to be monotone with respect to.
    """
    index = _find(wallet_id)
    if index is None:
        return 0
    rec = _slot(index)
    assert rec is not None
    off = _WALLET_ID_LEN + _ROOT_LEN
    return int.from_bytes(rec[off : off + _COUNTER_LEN], "big")


def set_root(wallet_id: bytes, root: bytes | None, counter: int = 0) -> None:
    """Record this wallet's root and counter.

    Nothing else is kept. The last attested TIME was not an independent signal -- anti-replay
    is the counter's job, and a malicious WM simply lies about the clock -- and the last
    attested COUNTER became redundant once writes stopped committing: every stored counter now
    arrives from an attestation, so it and the head counter are the same number."""
    if len(wallet_id) != _WALLET_ID_LEN:
        raise ValueError  # wallet_id must be exactly _WALLET_ID_LEN bytes

    index = _find(wallet_id)
    if index is None:
        for i in range(MAX_WALLETS):
            if _slot(i) is None:
                index = i
                break
    if index is None:
        # Every slot belongs to another wallet. Deliberately a no-op: see the module
        # docstring on why this refuses rather than evicting.
        return

    common.set(
        common.APP_WARD,
        index + _FIRST_KEY,
        wallet_id
        + (root if root is not None else bytes(_ROOT_LEN))
        + counter.to_bytes(_COUNTER_LEN, "big"),
    )


# --- the offline store ------------------------------------------------------------
#
# A DISJOINT KEY RANGE from the root slots above. Roots live at 1..MAX_WALLETS; records live
# at 0x40 upwards, with a gap between them on purpose. Sharing one range would make "how many
# wallets fit" and "how many records fit" the same number, and a record landing in a root slot
# would be read as a root -- a wallet_id match at the same offset is exactly the kind of
# collision that reads as ordinary operation.
_STORE_FIRST_KEY = const(0x40)

# 20 records, one shared pool across every wallet. Plaintext keeps a typical label record near 110
# bytes, so the store is a couple of kilobytes in practice.
MAX_STORE_ENTRIES = const(20)

# A VALUE MAY BE A WALLET POLICY, not just a label, and that sets the per-record cap. A BIP-388
# descriptor template runs 40-300 bytes and each key adds ~130 (`[fingerprint/derivation]xpub`), so
# 2-of-3 is ~430 bytes, 3-of-5 ~700, and 5-of-7 comfortably under a kilobyte.
MAX_VALUE_LEN = const(1024)
MAX_RECORD_LEN = const(1152)  # a value plus the identity framing around it

# THE GUARANTEE IS ON THE TOTAL, not on entries x record cap. Those two multiply to 23 kB, and the
# norcow sector is 32 kB on the smallest model (T3T2) -- shared with everything else the device
# stores, including a homescreen that may itself be 16 kB. Promising 20 maximum-size records would be
# promising flash that is not there, and the failure would arrive as norcow refusing to write, which
# reaches a host as a generic firmware error rather than as "the store is full".
#
# So the store bounds the BYTES it holds and lets the mix be whatever the user has: 20 typical labels
# (~2.2 kB), or five 1 kB policies, or any combination inside the budget. Whichever limit binds first
# -- slots or bytes -- reports the same "full", and the caller turns it into "erase an entry first".
MAX_STORE_BYTES = const(6144)

# Version 2 dropped entry_key, the counter and device_id from the record. THE KEYED PATH IS NOT
# THE QUEUE'S TO HOLD: it is what a leaf sits at in the TRIE, assigned when the change is published,
# and a queued change has not been published. Records are found by the IDENTITY they carry instead,
# and the path is derived from that identity at the one moment it is needed.
STORE_VERSION = const(3)  # the full form: the identity is in the record
STORE_VERSION_COMPACT = const(4)  # the identity is replaced by a 16-byte hash of it

# THE FULL FORM TRUNCATES wallet_id TO 7 BYTES; the root slots above keep all 16. The COMPACT form
# stores no wallet tag at all -- its name is a hash that already commits to wallet_id, so a tag would
# be the same information twice. What that costs is `store_list`: it cannot say whose a compact record
# is, so enumeration returns only the full form and everything that needs "my records" either works on
# names (get, put, erase, a named flush) or on the session claim ledger (a reconcile).
# The two answer
# different questions. A root slot is the wallet's authenticated head, written once and read on every
# verification, so its identifier costs 16 bytes eight times and buys the full 128 bits. A record
# carries the same tag 20 times, and all it has to do there is tell one wallet's records from
# another's on THIS device.
#
# 56 bits is ample for that. Accidental collision across 8 wallets is ~4e-16, and the adversarial
# case does not tighten it: computing a candidate wallet_id needs the SEED (it is a SLIP-21 leaf),
# and anyone holding the PIN can already read every record -- `storage.c` decrypts under a
# PIN-derived key without consulting this tag at all. It disambiguates; it does not authorise.
#
# The truncation lives HERE, not in `keys.derive_wallet_id`, because it is a property of this
# format. Callers pass the whole 16-byte id and this layer takes what it stores.
_STORE_WALLET_ID_LEN = const(7)

FLAG_PENDING = const(0x01)  # a local write that has not been published yet
FLAG_OFFERED = const(0x02)  # ...and it has already been handed to a host this side of a reconcile

# THE HEADER IS FROZEN ACROSS EVERY FUTURE VERSION: version(1) || wallet_id(7) || identity, where
# identity is len8(key_type)||key_type || len8(app_id)||app_id || len16(identifier)||identifier.
# This is load-bearing rather than tidy. A build that meets a record written by a newer firmware
# cannot parse it, and the erase rule forbids deleting what it cannot read -- so it must still be
# able to FIND that record and remove it when the user says so. Freezing the header is what makes
# "report incompatible, require explicit removal" possible instead of a blind wipe. Anything added
# later goes after the identity.
_STORE_VERSION_OFF = const(0)
_STORE_ID_OFF = const(1)
STORE_KEY_OFF = const(8)  # where the identity begins
STORE_PREFIX_LEN = const(8)


def store_prefix(wallet_id: bytes, version: int = STORE_VERSION) -> bytes:
    """The fixed part of the frozen header. The single point that decides its layout.

    FULL FORM: version || wallet_id[:_STORE_WALLET_ID_LEN]. Takes the WHOLE wallet_id and keeps its
    first bytes, so no caller has to know this format truncates and only one place decides how much
    of it is kept.

    COMPACT FORM: version, and nothing else. The name that follows is a hash that already commits to
    wallet_id, so a tag beside it would store the same fact twice.
    """
    if len(wallet_id) != _WALLET_ID_LEN:
        raise ValueError  # wallet_id must be exactly _WALLET_ID_LEN bytes
    if version == STORE_VERSION_COMPACT:
        return bytes([version])
    if version != STORE_VERSION:
        raise ValueError  # only the forms this build knows may be written
    return bytes([version]) + wallet_id[:_STORE_WALLET_ID_LEN]


def store_key_off(version: int) -> int:
    """Where a record's NAME begins, which is the one thing the two forms disagree about."""
    return 1 if version == STORE_VERSION_COMPACT else STORE_KEY_OFF


def _store_slot(index: int) -> bytes | None:
    return common.get(common.APP_WARD, index + _STORE_FIRST_KEY)


def store_find(wallet_id: bytes, candidates: "list[tuple[int, bytes]]") -> int | None:
    """This wallet's slot for any of `candidates`, or None.

    A CANDIDATE IS (version, key): the full form is named by its identity, the compact form by a hash
    of it, and a caller that knows the identity can compute both. Passing them together is what lets
    one lookup serve both forms without this layer knowing which is which -- the key is opaque bytes
    here, and its framing is `apps.ward.offline_store`'s business.

    Matches at FIXED OFFSETS. The version is part of the match rather than ignored, because it is what
    says which key the bytes at STORE_KEY_OFF are; `store_find_unreadable` is the path for a record
    whose version this build does not know.

    Matching on wallet_id AND the key, never the key alone: the same identifier under a different
    passphrase is a different wallet's entry, and serving one for the other is the failure this key
    scheme exists to prevent.
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
            # The FULL form is scoped by the tag it carries; the COMPACT form by its name, which is a
            # hash over wallet_id -- so a wallet mismatch there is a name mismatch and needs no
            # separate check. Both are checked against THIS wallet either way.
            if version == STORE_VERSION and rec[
                _STORE_ID_OFF:STORE_KEY_OFF
            ] != wallet_id[:_STORE_WALLET_ID_LEN]:
                continue
            off = store_key_off(version)
            if rec[off : off + len(key)] == key:
                return i
    return None


def store_get(wallet_id: bytes, candidates: "list[tuple[int, bytes]]") -> bytes | None:
    """The raw record, or None if this wallet has none matching `candidates`.

    Raw on purpose: deciding whether the bytes are USABLE -- known version, well-formed
    framing -- is the app layer's job, and returning None for an unreadable record would make
    "no such entry" and "cannot read this entry" the same answer. They are not, and the
    difference is what stops a corrupt record from silently reading as a miss.
    """
    index = store_find(wallet_id, candidates)
    if index is None:
        return None
    return _store_slot(index)


def store_bytes_used(exclude_index: "int | None" = None) -> int:
    """How many bytes every record in the store occupies, across ALL wallets.

    DEVICE-WIDE on purpose: the budget it feeds is flash, and flash does not care which wallet spent
    it. That does mean one wallet's records can fill the store and another's write then fails --
    which is already true of the shared slot pool, and is reported the same way.

    It leaks no more than the slot pool already does: a byte count, never a wallet or an identity.

    `exclude_index` leaves out the slot a replacement is about to overwrite, so replacing a record
    with a smaller one is never refused for the space the old one was using.
    """
    total = 0
    for i in range(MAX_STORE_ENTRIES):
        if i == exclude_index:
            continue
        rec = _store_slot(i)
        if rec is not None:
            total += len(rec)
    return total


def store_put(
    wallet_id: bytes, version: int, key: bytes, record: bytes, replaces: bytes | None = None
) -> bool:
    """Write a record, replacing this wallet's existing one for `identity`. False if full.

    FULL MEANS EITHER LIMIT: no free slot, or no room in `MAX_STORE_BYTES`. Both answer the same
    question -- can this be stored -- and the caller has the same thing to say about either.

    NEVER EVICTS. When there is no room the write FAILS and the caller reports it, because each
    occupant is either a value the user chose to keep or a change they confirmed and that is not
    published yet. Making room automatically would destroy one of those to satisfy the other,
    silently, and the user would learn about it by finding the entry gone.
    """
    header = store_prefix(wallet_id, version) + key
    if record[: len(header)] != header:
        raise ValueError  # record header must name the version, wallet and key it is stored under
    if len(record) > MAX_RECORD_LEN:
        raise ValueError  # a record past the cap breaks the capacity guarantee, see MAX_RECORD_LEN

    # `replaces` lets a write REPLACE the same entry held in the other form: switching a record to
    # compact must reuse its slot rather than leaving the old one behind under a different key.
    index = store_find(wallet_id, [(version, key)])
    if index is None and replaces is not None:
        other = (
            STORE_VERSION if version == STORE_VERSION_COMPACT else STORE_VERSION_COMPACT
        )
        index = store_find(wallet_id, [(other, replaces)])
    if index is None:
        for i in range(MAX_STORE_ENTRIES):
            if _store_slot(i) is None:
                index = i
                break
    if index is None:
        return False

    # Checked BEFORE the write, and against the store as it will be: a replacement pays only the
    # difference, because the bytes it is about to free are not spent any more.
    if store_bytes_used(exclude_index=index) + len(record) > MAX_STORE_BYTES:
        return False

    common.set(common.APP_WARD, index + _STORE_FIRST_KEY, record)
    return True


def store_delete(wallet_id: bytes, candidates: "list[tuple[int, bytes]]") -> None:
    """Remove this wallet's record matching `candidates`. A no-op if there is none.

    A PRIMITIVE, NOT A POLICY. It asks nothing and checks nothing beyond the identity: every caller
    must already have the user's confirmation in hand. Keeping the question out of here is what
    stops a future caller from acquiring the power to erase by accident -- there is exactly one
    path to this function that a user has agreed to, and it is `apps.ward.erase_cached_entry`.
    """
    index = store_find(wallet_id, candidates)
    if index is None:
        return
    common.delete(common.APP_WARD, index + _STORE_FIRST_KEY)


def store_find_unreadable(wallet_id: bytes) -> int | None:
    """A slot of this wallet holding a record THIS BUILD CANNOT PARSE, or None.

    THE ESCAPE HATCH THE FROZEN HEADER EXISTS FOR. A record written by a newer firmware carries its
    identity in a layout this build does not know, so it cannot be found by identity -- and without
    this it would occupy a slot forever, unnameable and unremovable, which is exactly the state the
    erase rule forbids. The version byte and the wallet_id are frozen, so it can always be found by
    those two alone.

    Deliberately NOT part of `store_delete`'s lookup: erasing a record nobody can read is a
    different question from erasing one the user can see, and only the confirmed path in
    `apps.ward.erase_cached_entry` may ask it.
    """
    if len(wallet_id) != _WALLET_ID_LEN:
        raise ValueError  # wallet_id must be exactly _WALLET_ID_LEN bytes
    for i in range(MAX_STORE_ENTRIES):
        rec = _store_slot(i)
        if rec is None or len(rec) < STORE_PREFIX_LEN:
            continue
        if rec[_STORE_ID_OFF:STORE_KEY_OFF] == wallet_id[
            :_STORE_WALLET_ID_LEN
        ] and rec[_STORE_VERSION_OFF] not in (STORE_VERSION, STORE_VERSION_COMPACT):
            # Only a FULL-shaped record can be attributed here: an unreadable record's layout is
            # unknown by definition, and the tag at this offset is the one thing the frozen header
            # promises. A compact record of a build this one does not know is not findable at all,
            # which is the price of dropping the tag -- and it is not reachable by name either, so
            # nothing can overwrite it silently.
            return i
    return None


def store_delete_slot(index: int) -> None:
    """Remove whatever occupies one slot. For the unreadable-record path only.

    THE CALLER MUST ALREADY HOLD THE USER'S CONFIRMATION -- see `store_delete`. This exists because
    a record that cannot be parsed cannot be named, so the only handle left is the slot it sits in.
    """
    if not 0 <= index < MAX_STORE_ENTRIES:
        raise ValueError  # slot index out of range
    common.delete(common.APP_WARD, index + _STORE_FIRST_KEY)


def store_read_slot(index: int) -> bytes | None:
    """Whatever occupies one slot, by index.

    The by-name reader is `store_get`; this is for callers that already hold a SLOT, which is the only
    handle that works for the operations identity cannot serve -- flipping a record's flags, and
    removing one whose form this build cannot parse.
    """
    if not 0 <= index < MAX_STORE_ENTRIES:
        raise ValueError  # slot index out of range
    return _store_slot(index)


def store_write_slot(index: int, record: bytes) -> None:
    """Rewrite the record in a slot IN PLACE, same length. For flag flips only.

    Why it exists: `FLAG_OFFERED` and `FLAG_PENDING` are changed by `flush_queue` and by a reconcile,
    neither of which has the record's identity in hand -- a COMPACT record does not carry one. Editing
    the bytes that are already there needs no identity at all, and it keeps the byte budget exactly as
    it was, which is why the length is required to match.

    THE CALLER MUST ALREADY OWN THE SLOT: it comes from `store_list`, so it is a record of the
    caller's own wallet. Nothing here re-checks that, in the same spirit as `store_delete`.
    """
    if not 0 <= index < MAX_STORE_ENTRIES:
        raise ValueError  # slot index out of range
    old = _store_slot(index)
    if old is None or len(old) != len(record):
        raise ValueError  # in-place means the same length; anything else goes through store_put
    common.set(common.APP_WARD, index + _STORE_FIRST_KEY, record)


def store_list(wallet_id: bytes) -> "list[tuple[int, bytes]]":
    """Every FULL-form record belonging to THIS wallet as (slot, record), in slot order.

    COMPACT RECORDS ARE NOT HERE, and cannot be: their name is a hash, so nothing in them says whose
    they are. That is the whole price of dropping their wallet tag, and it is paid by the callers that
    used to need enumeration -- `remaining` now counts what can be published unprompted, and a
    reconcile works from the session claim ledger, which is a stricter handle anyway.

    Scoped to one wallet with no way to ask for another: enumeration is the one operation where
    a missing filter leaks the existence of a hidden wallet's entries rather than merely
    failing.
    """
    if len(wallet_id) != _WALLET_ID_LEN:
        raise ValueError  # wallet_id must be exactly _WALLET_ID_LEN bytes
    out = []
    for i in range(MAX_STORE_ENTRIES):
        rec = _store_slot(i)
        if rec is None or len(rec) < STORE_PREFIX_LEN:
            continue
        if rec[_STORE_ID_OFF:STORE_KEY_OFF] == wallet_id[:_STORE_WALLET_ID_LEN]:
            # The SLOT comes with the record: a caller that wants to change a record's flags needs
            # the handle, and a compact record cannot be re-found by an identity it does not carry.
            out.append((i, rec))
    return out
