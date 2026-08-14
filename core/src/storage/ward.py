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
  the shrink discussed above: MAX_WALLETS is 8 because a record is 52 bytes, and a queue is
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
