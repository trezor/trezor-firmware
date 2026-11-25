# WARD roll-forward

A WM whose register goes back no longer holds transitions it accepted. That happens after a
restored backup, a failover onto a stale replica, or a lost register. Roll-forward brings the WM
back to its newest head. A Trezor of the wallet signs the accepted steps again for its current
session, and the host submits them to the WM as ordinary advances.

The Trezor's original WM signatures cannot be reused. Each is bound to the session it was made in,
and a restore ends every session. After a session ends, nobody can tell a stored signature for an
accepted step from one for a lost race (see
[a stored signature cannot be verified later](ward_transitions.md#consequence-a-stored-signature-cannot-be-verified-later)).
So roll-forward starts from what only the WM produced: its signed records of the steps it
accepted.

## Overview

1. **The Trezor detects the restore** during an ordinary sync.
2. **The host feeds it the accepted steps**, each with the WM's record of it, a page at a time.
3. **The Trezor checks every step**, the user approves once, and the Trezor signs each step again
   for its current session.
4. **The host submits the signatures** to the WM as ordinary advances.
5. **The Trezor shows the result**: how far the history was restored and when the WM last
   confirmed its last step.

```mermaid
sequenceDiagram
    autonumber
    participant H as host
    participant T as Trezor
    participant M as WM (restored to #10)
    Note over T: stored head #20
    H->>T: sync, with the WM's challenge
    T-->>H: fresh round nonce N, session proof
    H->>M: open the session N
    M-->>H: attestation of #10 under N
    H->>T: the attestation of #10
    Note over T: 10 is below 20: nothing adopted<br/>the restore is detected, starting at #10
    T-->>H: the WM is behind, the Trezor is at #20
    loop each page of steps
        H->>T: the WM's attested head, the next steps and the WM's record of each
        Note over T: check every step (see below)<br/>first page: the user approves the restore<br/>last page: shows how far, and when
        T-->>H: a signature of each step under N
        loop each step
            H->>M: advance the step with its new signature
            M-->>H: the WM's acceptance under N
        end
        H->>M: attest the advanced head under N
        M-->>H: attestation
    end
    H->>T: the attestation of #20
    Note over T: at its own head: adopted as usual
```

## Detection

The Trezor, not the host, decides that the WM was restored. When a sync attests a head below the
Trezor's stored head, the Trezor neither adopts it nor fails. It reports that the WM is behind,
with its own counter, and remembers the detection for this round, with the WM's head as the
starting point. The round stays open, but nothing can be adopted from it. Without that detection,
the Trezor refuses to sign anything again.

A Trezor that is not ahead of the restored WM, such as a fresh one, does not detect the restore and
adopts the WM's head as usual.

## The records

A WM record is any attestation the WM signed for exactly that step:

- **The acceptance of an advance.** It is signed under the session nonce and dated when the WM
  accepted the step.
- **An attestation from a later sync.** It is signed under that sync's nonce while the step was
  the head, and dated then.

Either way, the timestamp is when the WM vouched for the step; the WM itself keeps no time. The
host keeps one verified record per step, replicated with the links. The newest record replaces an
older one for the same step, so the kept time is the latest at which the WM vouched for that step.

## What the Trezor checks

Each page carries the WM's live attestation of its current head, under the round nonce of the
session the Trezor opened in this sync, and a run of steps, each with the Trezor's own MAC of it
and the WM's record of it.

The Trezor considers a step valid only if **both** of its checks pass:

1. **Its own MAC.** The MAC verifies under `K_auth`, so a Trezor of this wallet made the step. A WM
   cannot sign itself a history.
2. **The WM's signature.** The record verifies under the WM key over exactly this step, so the WM
   accepted it. A lost race or a publication held back has no record.

It also checks two things about the chain:

- **Contiguity.** The first step starts at the attested head, and each step starts where the
  previous one ended. A later page starts where the previous page ended.
- **Its own history.** No step jumps over the Trezor's stored counter, and a step that starts or
  ends at the stored counter has the stored root there. The Trezor re-authorizes history it is on,
  and steps beyond its head that continue from it; never a branch it would refuse.

It then signs each step again for the current session, keeping its kind: a revert stays a revert.

## What the user sees

- **Approval.** On the first page, after checking it, the Trezor shows "Restore WARD history":
  the WM's change number, its own, and how many changes that page signs again. Later pages of the
  same round need no new approval. Declining signs nothing, and the WM stays where it was
  restored to.
- **Result.** On the last page it shows "WARD history restored": the change number reached and,
  as "Last confirmed", the time of the WM's record of the last restored change, in UTC: when the
  WM last vouched for it, as far as the host's records go. The user can compare it with when they
  last made a change.

The user confirmed each change when it was made, and the WM accepted it. The approval is for the
restore itself: re-binding history the WM had lost to the current session.

## What the host does

The host rolls the WM forward during a sync on the wallet channel, when the Trezor reports that
the WM is behind:

1. Take the kept records of steps above the WM's head, newest first.
2. For each, walk the replica's links back from it. The WM's current head must lie on that walk.
   If no walk passes through it, the WM is on another branch, which is a rejoin case, and nothing
   is replayed.
3. Use the path up to the first step without a kept record.
4. Send the path to the Trezor a page at a time, with the WM's live attestation and each step's
   record, marking the last page.
5. Submit each returned signature to the WM as an advance, and keep each acceptance.
6. Before the next page, have the WM attest its advanced head under the same round nonce, because
   the Trezor's round is still open. That attestation only reads and leaves the session open.
7. When done, attest once more, hand it to the Trezor, and continue the normal sync, where the
   Trezor now adopts its head. The sync reports how many steps were restored, the counter reached,
   and the time of the last record.

A refusal by the Trezor or the WM, or a declined approval, ends the roll-forward there, and a
Trezor still ahead of the WM then fails the sync. The host can be configured not to roll forward.
The deprecated service channel does not roll forward.

## Trade-offs

- **For:**
  - The WM keeps one way in: a Trezor-signed advance in the current session.
  - The Trezor checks every step itself, and a hostile WM cannot sign a history the wallet never
    made.
  - The re-signed steps are bound to a session like any other authorization, so they expire with
    it.
- **Against:**
  - A Trezor must be connected, ahead of the restored WM, and the user must approve.
  - Each step costs a MAC check, a WM signature check and a new signature on the device.
  - The deprecated service channel does not support it.

## Alternative: the WM accepts its own records directly (not chosen)

The host presents the WM's records to the WM. The WM verifies its own signature over each step,
checks the predecessor against its head, and installs the step. No Trezor is involved.

```mermaid
flowchart LR
    H["host with the WM's<br/>acceptance records"] -->|"replay a record"| M["WM: verify its own signature,<br/>predecessor check, install"]
    M -.->|"no Trezor, no wallet MAC,<br/>no session"| M
```

- **For:**
  - It works while no Trezor is connected.
  - It is cheap: one signature check per step, on the WM.
- **Against:**
  - The WM gains a second way in that bypasses the Trezor. A WM bug or key compromise there is
    not checked by any wallet MAC.
  - Anyone holding the records can drive the WM forward with no device present, which widens the
    prefix choice below.
  - The records are not bound to any session, so they never expire.

## What stays open

- **Prefix choice (accepted gap).** Whoever holds the records chooses how far the WM is replayed,
  and after two restores also which branch. The WM then attests an old genuine head as current.
  Trezors whose stored counter is past it refuse it; a fresh or rarely synced Trezor accepts it.
  See [WM restore and roll-forward](gaps.md#wm-restore-and-roll-forward).
- **Open findings** in [gaps.md](gaps.md):
  [freshness after detected regression](gaps.md#freshness-after-detected-regression),
  [roll-forward consent and completion](gaps.md#roll-forward-consent-and-completion) (the
  approval counts only the first page, and the final screen shows before the host submits the
  signatures), [recovery dates](gaps.md#recovery-dates), and
  [recovery through relay clients](gaps.md#recovery-through-relay-clients).
- **A wallet the WM lost entirely** has no head to roll onto. Re-enrollment needs the Trezor's
  genesis authorization, which only a Trezor at counter 0 supplies.
