# Recovering manager history

Suppose a Trezor remembers change N and a restored manager reports an older change M, so M < N.
The device keeps its stored head. On the wallet channel, a compatible host can ask it to help the
manager recover the missing steps.

```mermaid
sequenceDiagram
    participant T as Trezor at N
    participant H as Local service
    participant W as Restored manager at M
    H->>T: Present the live attestation of head M
    T-->>H: Report that the manager is behind
    H->>T: Offer the steps from M to N with their manager records
    Note over T: Verify the path and ask the user to approve recovery
    T-->>H: Release fresh authorizations after approval
    H->>W: Resubmit each step in order
    W-->>H: Attest the head actually reached
    H->>T: Return that attestation to complete the sync
```

## Evidence for each step

The host supplies a continuous path from the manager's restored head. For each step the Trezor
checks the wallet authentication tag and a signed manager record for the same predecessor and
successor. The tag proves a wallet device authorized the step, including whether it was a revert.
The manager record rules out writes that lost a race or were never submitted.

The path cannot skip the device's stored counter and must match its root if it reaches that
counter. Recovery uses fresh write authorizations because restoring the manager ends its previous
session. The manager checks each predecessor, and the host obtains a fresh attestation.

## What the user approves

The first screen shows the manager's and device's positions and the number of changes on the first
page. The Trezor requests user approval and releases recovery signatures to the host. 
The screen shows the last step prepared for submission and the date
the manager last confirmed it. A subsequent live sync establishes how far the manager advanced.
For example, if the host has records only through change K, with M < K < N, the manager can
advance to K. The device at N still reports that the manager is behind. The steps accepted up to K
remain in place.

## Reverting and rejoining

A **revert** restores a verified historical root under a new counter. The Trezor checks the validity 
of the previous transition and the manager's historical evidence before asking for a confirmation. 
If the manager has regressed due to restore, the rollback requirement may be undetected.

A **rejoin** switches between diverging histories. The Trezor verifies their last common state and
asks the user to confirm how much local history to discard before adopting the manager's branch.
Changes discarded this way can later be re-added like
[changes that arrive after a revert](#changes-that-arrive-after-a-revert).

### Reverting to an attested state

When a writer's changes have not reached Evolu, the replica cannot rebuild the manager's head N and
the host cannot tell whether the changes are late or lost. The user decides. The host presents a
kept manager attestation of an earlier head M, which carries the time T the manager signed it. The
Trezor verifies the signature and shows the date T beside the manager's current head. The manager's
signature alone does not authorize the revert: the user approves it on the Trezor. The screen says
that N − M changes made after T leave the current state, and that the Trezor can offer to re-add
them if they arrive later. The count is exact unless a revert lies between M and N. If the user
approves, the device authorizes a revert from N to a new head N + 1 with the root of M. The replica
builds N + 1 from its tree at M, so it does not need the missing changes.

The changes between M and N are not erased: if they arrive, the replica keeps them on a dead
branch.

Today the Trezor verifies a revert by walking the transitions from the manager's head back to the
target, and its screen shows change numbers rather than a date. It cannot revert past a step whose
record has not arrived, and wardd cannot yet publish a revert.

### Changes that arrive after a revert

Suppose the changes between M and N reach Evolu after the user accepted the revert to M. The
manager's history runs from M to N, then reverts to N + 1, and may continue with later writes. The
changes between M and N form a dead branch. The replica holds them and can prove them against
their own roots, but they are not part of the current state.

The changes are re-added, not restored by a second revert. A revert back to N would also discard
every change made after the first revert.

The host reports the dead-branch changes it holds. The Trezor authenticates the branch from the fork
point M, the last state it shares with the current history: it verifies each transition's wallet
authentication tag from M up to the branch head, and each entry against the root of the transition
that wrote it. The branch must account for all N − M changes before the Trezor offers any of them,
so a host cannot present part of it as the whole. A write counter alone is not enough to decide
anything. For each changed entry the Trezor displays the entry in full: its identifier, its value at
M, the late value and the current value.

| What the device finds | What happens to the entry |
| --- | --- |
| The current value equals the late value. | Nothing to re-add. Nothing is published. |
| The current value equals the value at M. | The user can re-add the late value. Approval publishes it as a new change. |
| The current value differs from both. | The device shows all three values. Re-adding the late value overwrites the current one and requires confirmation. |

Re-added entries receive new counters above the current head. The Trezor that wrote the changes
adopted N before the revert. On its next sync it adopts the revert, warns that changes were
reverted, and can offer the same re-adding.

### Closing a dead branch

Without a record of the user's decisions, every sync would offer the same branch again. Once the
user has decided every entry on the branch, re-adding it or not, the Trezor closes the fork: it
authenticates a closure record naming the fork point M and the branch head N with their roots.
The host stores the record in Evolu beside the transitions, so every host and every Trezor of the
wallet sees it. A Trezor that verifies a closure for a branch does not offer that branch again.

If the user stops before deciding every entry, the branch stays open and is offered again. Entries
already re-added then show the current value equal to the late value and need no question.

The closure only prevents repeated questions. A host can still withhold a dead branch or its
closure; withholding the closure only repeats the questions.

Re-adding dead-branch entries and closing a fork remain proposals. Today the changes stay on the
dead branch until the user enters them again.
