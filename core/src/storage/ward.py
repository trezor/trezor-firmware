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

Each slot carries the root, the anti-rollback counter and the last attested time, because
a root alone does not identify a moment: roots repeat whenever contents repeat, so an old
signature naming today's root would otherwise be replayable (ward-design.md 2.4, 8.2 --
bind on the counter, not the root).

FIXME(ward): the root and the timestamp probably do not belong in persistent storage at all.
Only the counter is irreducible.

The ROOT is DERIVABLE. A sync round re-establishes it from the WM's attestation plus the
root the host supplies, because the mac binds the two together and only a seed-holding
device can compute one. Nothing here is the sole surviving copy of anything.

The TIMESTAMP is not an independent security signal. Anti-replay is the counter's job; a
malicious WM simply lies about the time, and an honest WM whose clock regresses without its
counter regressing is not an attack. Its one remaining consumer is the recovery screen's
"going back about N hours" -- genuinely useful, since a counter delta of 5 does not say
whether that is five minutes or five months, but that is a UX signal, not a check.

THE PAYOFF IS SIZE. The record is wallet_id(16) + root(32) + counter(4) + timestamp(8) = 60
bytes, and MAX_WALLETS is small because of it. At 20 bytes the same flash holds roughly three
times the wallets, which directly relieves the refuse-a-newcomer policy above -- more wallets
protected, which is the thing that policy is currently trading away.

TWO THINGS PERSISTENCE BUYS TODAY, both needing an answer first:

  The same-counter FORK check in `reconcile`. Two devices of one wallet can each write at
  counter N+1 from the same base, yielding two different-but-valid (counter, mac) pairs.
  Comparing the attested root against the stored one is what makes that a refusal rather
  than a silently adopted fork and a lost write. Without a stored root the check cannot run,
  and the mac will not catch it -- both pairs are genuine.

  No unverified window after boot. Without a stored root the device verifies nothing until a
  round completes, and `common._verify_against_root` currently treats "no root" as "skip",
  which is the failure direction that hides. Dropping the root therefore wants reads to FAIL
  CLOSED until a round completes -- stricter than today, not weaker, and aligned with the
  attested-root work the warning in `common.py` is waiting on.

The timestamp's place in the ATTESTATION PREIMAGE is a separate question from its place here:
dropping it from storage needs no wire change.

THE OFFLINE QUEUE: DECIDED FOR NOW, WITH ITS BLOCKERS LISTED. MVP is online-only, so the
queue lives in EVOLU rather than on the device -- which duplicates the leaf data there, and is
accepted for that reason alone. Flash is the intended destination later. Each candidate home
and what stands in its way:

  RAM is not actually available at the needed size. RAM that survives between requests is the
  session cache, and its slots are FIXED-SIZE, statically declared as a literal tuple in
  `cache_codec.py` / `cache_thp.py` and enforced by `utils.ensure(len(value) <= fields[key])`.
  The largest existing slot is 128 bytes; WARD's round is 77. An intent is an entry_key plus a
  value up to the 4096-byte AEAD bucket, so a queue of them fits nothing, and a module global
  is not an option -- `trezor.wire` runs `unimport_end()` between workflows, which is what put
  the sync round in the cache to begin with. A RAM queue therefore means a declared maximum of
  two or three small intents, not a queue.

  A RAM queue also makes the confirmation LIE: the user holds to confirm, the session drops,
  the change is gone and nothing said so. It needs its own screen wording, not the write's.

  FLASH, when it comes, must be keyed by wallet_id exactly as the root is -- otherwise a
  passphrase switch applies one wallet's queue to another. It also spends the same budget as
  the shrink discussed below: MAX_WALLETS is 8 because a record is 60 bytes, and a queue is
  orders of magnitude larger, so the two trade against each other directly.

  EVOLU works because the sealed leaf is itself an AUTHENTICATOR: the AEAD's AAD is
  domain || entry_key || key_type, so only a holder of K_data -- every device of the wallet,
  nobody else -- can produce a valid tag. A host cannot inject a fabricated write intent.
  Deletes are the exception and need the sealed tombstone plus intent MAC described in
  `delete_entry.py`; without those, uploading queued deletes lets a host delete anything.

WHATEVER THE HOME, TWO THINGS HOLD. A queued intent is an INTENT, not a transition: a device
with no host cannot pull, so it cannot prove current state and cannot derive a root. And an
intent formed against root R is not applicable to R' -- its proof material and derived root are
relative to R -- so reconnecting means RE-DERIVING each one against current state, which is
mandatory machinery rather than an optimisation.

KNOWN AND ACCEPTED: ATOMICITY AND CONSENT TRANSFER. A queued batch has no transaction to
apply under -- Evolu's CRDT offers none -- so partial application can leave a state the user
never approved. And when another device integrates intents, either it applies them silently,
so the user never learns, or it re-confirms what was already approved once. Both are to be
resolved by `rollback` when they go wrong, which is one more reason that path is load-bearing
rather than an escape hatch (see `apps/ward/rollback.py`).

THE PROPOSED ENABLER, AND WHY IT IS NOT YET ESTABLISHED. The argument for dropping the root
is that if writes commit only on WM CONFIRMATION -- change held pending until the WM
acknowledges the next (counter, root), another device forced to synchronise first or be
refused -- then a device never holds an unconfirmed head, so the fork check above has nothing
to check and the root is purely derivable. That much holds. What does not follow is that the
root is then free to drop, for three reasons, in increasing order of how much they cost:

  ROLLBACK IS CHECKED AGAINST THE DEVICE'S OWN HEAD. `rollback` verifies the supplied
  auth_commit describes (counter - 1, to_root) -> (counter, head) where `head` is what THIS
  device holds. With no persisted root, `head` reads as the empty tree after a reboot and
  every rollback is refused. Recovering the head first needs a sync round -- so rollback
  would require an attestation, which is precisely the property its design refuses: an escape
  that needs the WM is unavailable in the situation it exists for.

  SO THE TWO CHANGES MUST LAND TOGETHER, not in sequence. While a device can still commit
  ahead of the WM, the attestation it would need to re-establish its head is refused by the
  counter floor in `ingest` -- no root, therefore no rollback, therefore permanently stuck.
  Dropping the root BEFORE commit-on-confirmation would ship a brick.

  AND THE HOST MUST KEEP A HEAD LOG. In the durability case (see `rollback`), the leaves are
  gone but recovery still needs (counter, root, auth_commit) to re-establish the head and then
  demote it. That makes retaining those 32 bytes -- separately from the leaf data, so it
  survives losing the data -- a REQUIREMENT on the host rather than a convenience. The host
  model already keeps exactly this shape (`WardTrie.links`), so it is satisfiable, but it has
  to be stated before `@trezor/ward` is written rather than discovered afterwards.
"""

from micropython import const

from storage import common

_WALLET_ID_LEN = const(16)
_ROOT_LEN = const(32)
_COUNTER_LEN = const(4)
_TIMESTAMP_LEN = const(8)

# 8 wallets at 60 bytes each. Raising this costs flash and nothing else.
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


def get_timestamp(wallet_id: bytes) -> int:
    """The last attested time this wallet accepted, in seconds. Zero if never synced.

    Zero means "nothing to be monotone with respect to", which is the honest state for a
    wallet that has never seen an attestation -- and the one no automated check can help.
    """
    index = _find(wallet_id)
    if index is None:
        return 0
    rec = _slot(index)
    assert rec is not None
    off = _WALLET_ID_LEN + _ROOT_LEN + _COUNTER_LEN
    return int.from_bytes(rec[off : off + _TIMESTAMP_LEN], "big")


def set_root(
    wallet_id: bytes, root: bytes | None, counter: int = 0, timestamp: int = 0
) -> None:
    """Record this wallet's root, counter and last attested time."""
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
        + counter.to_bytes(_COUNTER_LEN, "big")
        + timestamp.to_bytes(_TIMESTAMP_LEN, "big"),
    )
