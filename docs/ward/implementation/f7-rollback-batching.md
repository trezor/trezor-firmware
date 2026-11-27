# F7 Rollback and batching

F7 covers every way the Trezor's head moves other than a single live write: offline changes queued
on the device and published one by one or as a batch, reverts to an earlier verified root, rejoins
onto the manager's branch, and roll-forward of a restored WARD Manager (WM). All build on the
trusted head and chain walk ([F5](f5-chain-history.md), [F6](f6-freshness.md)).

Invariants:

- A commit advances the counter by its number of changes (one to eight); a revert advances it by
  exactly one and restores an earlier root
  ([why](../ward_transitions.md#why-commits-count-changes-and-reverts-count-one)).
- The stored head moves only through verified history. Reverts, rejoins and discards need explicit
  confirmation on the Trezor.
- A queued change has landed only when its exact offered transition is verified, never because
  another writer reached the same counter.
- Every authorization is bound to its predecessor and write session and lands at most once.

## F7.1 Implement persistent pending edit management

Keep queued changes on the device, apart from the head, until a verified adoption shows they landed
or the user discards them
([keeping a contact while offline](../user_story.md#keeping-a-contact-while-offline)).

- One record per entry of the active wallet: a queued change or a pinned copy, plus an "offered"
  flag once its authorization went to a host. A queued change holds entry identity, new value and
  base counter; it needs no proof. A compact form keeps only a keyed hash of the identity and is
  published only when the host names the entry.
- A claim journal holds one claim per offer: record slot, claimed counter, released wallet tag and
  record generation.
- Fixed capacity, never evicting; a full store or journal refuses the write or offer. Only
  settlement clears "queued", only a confirmed erase removes a record, and an unreadable record is
  never treated as absent.
- A change restored from a [backup](../user_story.md#backing-up-local-work) has no base, so any
  differing published value is a conflict.

## F7.2 Prepare and validate batch transitions

Turn queued changes into one transition the WM can accept. Publication needs a head adopted in this
session from a live attestation (the stored head in the MVP); signing clears freshness, so each
further publication needs a new sync, or the host asks for a batch on the wallet channel.

- Fold up to eight eligible queued changes in store order into one step F → F + n: verify each
  against the root built so far, derive the next root, seal the value with write counter F + i.
  Stop before exceeding the one-reply byte budget; always take the first change.
- One wallet tag and one WM authorization cover the batch; intermediate counters are never heads. A
  host replaying the changes rebuilds the same root [independently](../ward-trie.md).
- A change conflicts when its entry was published with a different value after its base. Only the
  first change may raise the conflict screen; a later conflict ends the batch before it. A change
  whose published value already matches settles at once as a pinned copy.
- Validate everything, check journal room, file all claims, then release the reply. Any failure
  leaves nothing filed or flagged.

## F7.3 Implement batch confirmation and cancellation

Decide each queued change's fate. The user confirms a change when queueing it; publication shows no
further screen unless there is a conflict.

- Before saving an adopted head, settle every claim: landed only if its wallet tag is among the
  transitions verified on the way. Landed changes become pinned copies; others are offered again on
  the new head. A batch that lost a race fails the WM predecessor check whole and returns whole.
- A claim settles only a record of the same generation. If a newer value was queued after the offer
  and the old claim landed, the newer change's base moves up to the claimed counter.
- On conflict: publish the queued value, keep the published one, or defer (stops the flush).
- Discarding needs a held confirmation and erases the record and its claim. It cannot revoke an
  authorization a host already holds; if that lands, the next sync shows it.

Known gaps: deletion and revert can hide an intervening edit from the conflict check
([publication gaps](../gaps.md#publication-and-reads)).

## F7.4 Authorize reverts with monotonic counters

Restore an earlier verified root M: with the WM at N, the revert goes N → N + 1 carrying M's root,
under a revert domain tag. The WM counter stays strictly increasing.

- Verify the target by a walk back from the attested WM head to M (every step except the one the
  live attestation pins backed by a WM record), or by a saved attestation of the target with its
  wallet authorization ([reverting to an attested state](../ward_roll_forward.md#reverting-to-an-attested-state)).
  The device's own head must lie on that history.
- The screen shows device, WM and target counters, the number of discarded changes and, where
  known, the Manager-signed date; approval needs a hold.
- Authorizing a revert ends the write session: the round closes and the session's WM head is
  forgotten. The host submits the revert and a new sync adopts it with a warning
  ([sessions](../ward_transitions.md#sessions)).
- **Demotion.** If the WM is behind the device, N + 1 can be at or below the stored counter. Consent
  for that exact transition, from the current stored counter, is the only exemption from the floor.
  It is session-only and spent by any adoption.

## F7.5 Implement fork and missing-history recovery

Recover from a lost branch, a WM that lost history, or changes missing from Evolu, keeping the
stored head until the way forward is verified and any loss approved.

- **Rejoin** ([reverting and rejoining](../ward_roll_forward.md#reverting-and-rejoining)). The WM is
  on another branch at or above the device. Both branches must share the root at the named fork
  point K and differ one step above it. After a hold the device adopts the WM head; changes offered
  on the lost branch are offered again.
- **Roll-forward** ([recovering manager history](../ward_roll_forward.md)), only in a round that
  found the WM behind. Each step continues the previous one with a valid wallet tag and matching WM
  record and matches the stored head where it reaches it
  ([evidence](../ward_roll_forward.md#evidence-for-each-step)). One approval covers all pages; the
  device re-signs each step for the new session, clears freshness and adopts nothing.
- **Late Evolu data** ([data loss in Evolu](../ward-trie.md#recovery-after-data-loss-in-evolu)).
  The user may revert to an attested state (F7.4). Later arrivals are
  [re-added](../ward_roll_forward.md#changes-that-arrive-after-a-revert) and the branch
  [closed](../ward_roll_forward.md#closing-a-dead-branch); both are proposals.

## F7.6 Protect recovery against authorization replay

Every authorization must move the wallet only from the state it was made for to the state the user
approved, at most once. Both authenticators cover kind, wallet identity and both heads; the WM
authorization also covers the session nonce and is accepted only in that
[session](../ward_transitions.md#sessions) from the WM's current head.

| Operation | Binding |
| --- | --- |
| Revert | Starts at the attested WM head; consent names the exact transition; it ends the session, so each revert needs its own sync. |
| Rejoin | Only from an attested round; adoption closes the round. |
| Roll-forward | Only in the round that detected the restore; each page starts at the freshly attested WM head. |
| Lost race | A wallet-authenticated [retry token](../ward_transitions.md#competing-writers); any new authorization is on the current head. |
| Queued change | A claim settles only its exact transition and record generation. |

Attestations, consent and roll-forward state never outlive the connection. A backed-up queued change
has no replay bound; the user confirms the restore.

## Open questions

- A demoting revert accepted by the WM but not adopted in its session cannot be adopted until the
  WM moves above the device. Should consent persist?
- Should discarded changes after a rejoin be re-added as after a revert?
- How to close the settle-then-save window ([gaps](../gaps.md#publication-and-reads)).

## Related

- [Transitions and sessions](../ward_transitions.md),
  [recovering manager history](../ward_roll_forward.md)
- [Security gaps](../gaps.md) and [threat model](../threat_model.md#accepted-security-limitations)
