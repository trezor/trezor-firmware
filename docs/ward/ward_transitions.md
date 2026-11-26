# Transitions and sessions

A transition identifies the wallet and its starting and resulting heads. Publishing advances the
counter by the number of entries it writes, at most eight in one batch. A revert advances it by
one however many entries it restores. Verifiers check only that each step advances by one to
eight; the count itself comes from the writing Trezor.

The manager accepts one successor per head, so along its history each counter names one state. A lost race, a manager restored from backup, or the MVP without a manager can still produce different roots at the same counter; the root tells them apart.

## Why commits count changes and reverts count one

**Commits advance by the number of changes.**

- Pros:
  - Batching does not change the result: the same changes, one by one or batched, end at the same
    counter and root.
  - The counter counts the user's changes, so screens can show it directly.
  - After a sync failure, N − M tells exactly how many changes are missing, even before their
    records arrive.
  - When late records arrive, the Trezor can check that the dead branch holds all N − M changes.
- Cons:
  - Only the writing Trezor knows the count. Others check only that a step advances by one to eight.
  - Counters inside a batch are never heads, so a chain walk must land on its target exactly.

**Reverts advance by one.**

- Pros:
  - A revert does not need to know what changed, so it works when records are missing.
  - It restores the exact earlier root, so earlier proofs against that root stay valid.
- Cons:
  - Across a revert, counter differences no longer equal the number of changes. A count shown on
    screen that spans a revert is off.
  - Restored entries get their old write counters back, so a write counter can move backwards.
    Re-adding therefore compares values, not counters.

## From approval to adoption

Suppose a user changes an address label while the Trezor and manager both hold head M. The
device can authorize head N, with M < N (N = M + 1 for a single change), before either party
adopts it.

```mermaid
sequenceDiagram
    participant T as Trezor
    participant H as Local service
    participant W as WARD Manager
    T->>H: Request the current entry and proof
    H-->>T: Encrypted entry with proof, or proof of absence
    Note over T: Verify at head M and show the proposed edit for approval
    T->>H: Sealed change and authorizations for M to N
    Note over T: Still at M, freshness indication cleared
    H->>H: Store the encrypted change
    H->>W: Submit the authorized transition
    W-->>H: Advance to N and return a signed receipt
    Note over T,W: On the next sync
    H-->>T: Fresh manager attestation and wallet history
    T->>T: Verify the step and adopt head N
```

The wallet authentication tag lets another Trezor verify the step later. The public signature lets
the manager check the current writer and predecessor. If the reply is lost, the device can learn on
sync whether its step landed. In the MVP the service checks the public signature itself, and the
device adopts by verifying the chain back to its stored head.

## Sessions

The Trezor signs the manager's single-use challenge and its own fresh nonce. The manager verifies
the signature, consumes the challenge and replaces the wallet's previous write session. A read-only
attestation leaves the active session in place.

A delayed write can land while both its session and predecessor remain current, even after the
device disconnects. A write displaced by another session or a competing change requires a new sync.


## Competing writers

Suppose a second Trezor opens a session and publishes a change before the first Trezor's label edit
reaches the manager. The first device syncs to the winning head. Its host can then present the
original edit with a wallet-authenticated retry token. The device verifies the token and checks
the entry at the newly adopted root.

| What the device finds | What happens to the edit |
| --- | --- |
| The entry has the same write counter as at approval. | The device can authorize the edit against the new head without asking again. |
| The counter changed and the intended value is already there. | The edit is complete. Nothing is published. |
| The counter changed and the values differ. | The device shows both values. Overwriting the published value requires confirmation. |

Device on a competing branch requires proof of descent from its own head. A higher counter alone is insufficient.
