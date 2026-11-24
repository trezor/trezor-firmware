# WARD transitions and sessions

A transition moves a wallet's WARD head from `(from_counter, from_root)` to
`(to_counter, to_root)`. The Trezor authorizes every transition twice: once for other Trezors
of the wallet, and once for the [WARD Manager](ward_manager.md). The WM authorization is bound to
a session that the Trezor opens when it syncs.

## The transition

Both authorizations sign the same bytes:

```
transition_preimage = len8(tag) || tag || ward_id(32)
                      || from_counter(4B BE) || from_root(32)
                      || to_counter(4B BE)   || to_root(32)
```

`ward_id` is the Ed25519 public key of the wallet's `K_sig`. An empty tree is encoded as
`EMPTY_ROOT = sha256(0x02)`. A transition raises the counter by 1 to `MAX_BATCH` (8): one change,
or a batch of queued changes. A revert also raises the counter. It carries an older root under a
new counter. Within one WM register history, a `(counter, root)` pair therefore occurs once.

| Authorization | Key | Tag | Appended | Verified by |
| --- | --- | --- | --- | --- |
| `auth_commit` | HMAC-SHA256 under `K_auth` | `WARD COMMIT v3`, `WARD REVERT v3` | nothing | other Trezors of the wallet, walking the chain |
| `wm_sig` | Ed25519 under `K_sig` | `WARD WM COMMIT v5`, `WARD WM REVERT v5` | the session nonce (32 bytes) | the WM, with `ward_id` |
| `head_init_sig` | Ed25519 under `K_sig` | `WARD WM INIT v4` | nothing | the WM, once, at enrollment |
| MVP host step | Ed25519 under `K_sig` | `WARD STEP v2` | nothing | wardd without a WM |

`head_init_sig` is a self-transition `(0, root) -> (0, root)`. The WM enrolls a wallet only at
genesis. Code: [`apps/ward/cas.py`](../../core/src/apps/ward/cas.py).

## The WM attestation

The WM answers a sync by signing the step that reached its head, bound to the Trezor's nonce:

```
b"WARD ATTEST v1" || 0x07 || nonce(32) || ward_id(32)
  || from_counter(4B BE) || from_root(32) || to_counter(4B BE) || to_root(32)
  || timestamp(8B BE)
```

The signature uses the WM key. Release firmware carries a placeholder key and refuses every
attestation. Debug and emulator firmware accept the debug key. Code:
[`apps/ward/attest.py`](../../core/src/apps/ward/attest.py).

The same statement serves three purposes, distinguished by where the nonce comes from:

- **Live attestation.** The nonce is the Trezor's open round. The Trezor adopts the head only
  from this.
- **WM acceptance record.** The WM signs the new step under the session nonce when it accepts an
  advance. Roll-forward presents it after a restore.
- **Cached attestation or rollback receipt.** A host keeps a past attestation. It proves that the
  WM once held or accepted that step. `WardCatchUp` and `WardRollback` verify it with the nonce it
  carries and treat it as history, never as currency.

## Sessions

A session binds the Trezor's WM authorizations to its most recent sync. Only the Trezor picks
the nonce. The WM never does.

1. **The Trezor opens a session.** For each sync it draws a fresh 32-byte round nonce:
   `WardSyncAck.nonce` on the wallet channel, and `WardSyncRequest.nonce` or `WardPublish.nonce` on
   the service channel.
2. **The WM records it.** The WM attests its head against that nonce and keeps it as the
   wallet's session nonce. A later sync by any Trezor of the wallet replaces it.
3. **The Trezor latches it.** After verifying the attestation, the Trezor stores
   `(counter, root, nonce, timestamp)` in its session cache (`round.wm_head`).
4. **The Trezor binds each authorization.** It mints every `wm_sig` over
   `transition_preimage || nonce` and refuses to mint one without a session: "no WM session; sync
   first".
5. **The WM checks the binding.** It accepts an advance only if `wm_sig` verifies against the
   session nonce it holds, under the commit or revert tag, and the `from` end is its current head
   (compare-and-swap). The host may name the session it believes is current; see
   [the optional session field](#the-optional-session-field).
6. **The WM signs its acceptance.** It returns an acceptance record: the attestation of the new
   step under the session nonce. The host keeps it.

A head change does not end the session, so one session can carry several transitions. On the
service channel, each publication carries a fresh nonce. The WM attests the new step against it,
and that nonce becomes the session nonce on both sides.

### What a session prevents

An authorization that did not land in its session is dead once the wallet syncs again. Two cases:

- **A lost race.** Two Trezors mint from the same head and one lands first. The loser's `wm_sig`
  fails the compare-and-swap, and the next sync ends its session.
- **A publication the host held back.** It is refused after any later sync.

The session nonce is volatile WM state. A restored backup, a failover, or a lost register drops
it. So a restored WM accepts none of the `wm_sig`s minted before the restore. What the WM had
accepted comes back by [roll-forward](#roll-forward).

Tests:

- **Firmware device tests** in `tests/device_tests/misc/test_ward.py`:
  - `test_ward_attack_a_write_from_an_ended_session_is_refused`: a held write is refused after the
    same device syncs again.
  - `test_ward_attack_another_devices_sync_ends_this_devices_session`: the same, after another
    device of the wallet syncs.
  - `test_ward_attack_a_revert_from_an_ended_session_is_refused`: a held REVERT is refused after a
    new sync.
  - `test_ward_a_write_is_bound_to_the_latest_sync`: the Trezor binds to its latest attestation.
- **wardd tests** in the "ADVERSARIAL: a transition is invalidated by a new sync" group of
  `host.test.ts`, and in `service.test.ts`: the host and the WM each refuse a result whose session
  has ended.

### What a session does not prevent

- **Concurrent Trezors.** A sync by one Trezor of the wallet ends the session of every other.
  Their next publication gets a conflict, and they sync again.
- **Delay.** Within a session, a host may delay a publication while nothing else lands.
- **A reopened nonce.** The WM cannot tell a fresh Trezor nonce from an old one that a host
  replays. After a restore brings back a head, a host can ask the WM to attest that head under
  the nonce of an old session and then submit that session's unlanded authorizations. This is an
  accepted gap: closing it needs a WM high-water mark that a restore cannot take back, and no
  acceptable store for one exists. See
  [WM restore and roll-forward](gaps.md#wm-restore-and-roll-forward).
  `test_known_gap_a_host_can_reopen_an_old_session` in `tests/test_ward_wm.py` pins the behavior.

## Why the session is part of the signature

The WM checks three things before it advances:

- **Who:** the signature verifies under `ward_id`.
- **Where:** the `from` end is its head, by compare-and-swap.
- **When:** the signature is bound to the current session.

The compare-and-swap alone makes an authorization single-use within one register history,
because the counter only rises. It does not stop an authorization from landing **late**:

- **Late but valid.** An authorization minted on head H stays valid for as long as H is the head.
  A host can hold it, a lost race can wait, and a restore that brings H back makes it valid again.
- **What the session adds.** Binding the signature to the nonce of the Trezor's sync limits it to
  that sync. The next sync, by any Trezor of the wallet, ends it. A restore ends it too, because
  the session nonce is volatile.

The nonce lives inside the signature. That is the only place the WM can check it: the Trezor never
sends a separate field the WM would have to trust.

### Consequence: a stored signature cannot be verified later

The session nonce is not part of the transition the Trezor sends. A result carries `counter`,
`auth_commit` and `wm_sig`, but no nonce. A stored `wm_sig` can therefore be verified only by a
party that knows which session it was minted in:

- **The WM:** only while that session is current.
- **wardd:** only for the sessions it ran itself.

After the session ends, nobody can tell a stored `wm_sig` for an accepted transition from one for
a lost race. So the stored signatures cannot be used to rebuild the WM's history. Rebuilding has
to start from what only the WM produced: its responses, the acceptance records and attestations
that sign each step it accepted.

## Roll-forward

A WM whose register goes back no longer holds transitions it accepted. That happens after a
restored backup, a failover onto a stale replica, or a lost register. A host that kept the WM's
records of those transitions can bring the WM back. There are two ways to do it.

### Option A: the Trezor signs the transitions again (implemented)

It runs in four stages:

1. **The Trezor detects the restored WM during a sync.** When `WardIngestAttestation` attests a
   head below the Trezor's stored head, the Trezor does not adopt it and does not fail. It
   answers `wm_behind`, with its stored counter, and records the detection for this round. The
   round stays open but is not attested, so nothing can be adopted from it.
2. **The host feeds the accepted transitions.** Oldest first, in `WardRollForward`, at most 16
   per message. The Trezor refuses `WardRollForward` in a round without that detection.
3. **The user approves.** On the first page, after checking it, the Trezor shows "Restore WARD
   history": the WM's change number, its own, and how many changes it will sign again.
4. **The Trezor tells the result.** On the last page (`final`), it shows "WARD history
   restored": the restored change number and when the WM accepted the last restored change, in
   UTC. It also returns that time as `last_timestamp`. The user can see how recent the restored
   history is.

Each `WardRollForward` message carries:

- the WM's live attestation of its current head, against the round nonce the Trezor just picked;
- each transition with its `auth_commit` and the WM's acceptance record of exactly that step
  (`WardChainLink.acceptance`).

The Trezor considers a transition valid only if **both** of its checks pass:

1. **Its own MAC.** The `auth_commit` verifies under `K_auth`, so a Trezor of this wallet made the
   step. A WM cannot sign itself a history.
2. **The WM's signature.** The acceptance record verifies under the WM key over exactly this step,
   so the WM accepted it. A lost race or a publication held back has no record.

It also checks two things about the chain:

- **Contiguity.** The first step starts at the attested head, and each step starts where the
  previous one ended.
- **Its own history.** A step that reaches or crosses its stored counter agrees with its stored
  head. The Trezor re-authorizes only history it is on.

It then signs each step again under the round nonce, with the step's original tag: a revert stays
a revert. It returns the signatures in `WardRollForwardAck`, and the host submits them to the WM as
ordinary advances. Before the next page, the host has the WM attest its advanced head against
the same round nonce. A later page must start where the previous one ended, and needs no new
approval. When roll-forward ends, the host ingests a fresh attestation and the Trezor reconciles
as usual.

The user confirmed each change when it was made, and the WM accepted it. The approval is for the
restore itself: re-binding history the WM had lost to the current session. Code:
[`apps/ward/roll_forward.py`](../../core/src/apps/ward/roll_forward.py), wardd
`WardHost.rollForward`. See [roll-forward in the WM](ward_manager.md#roll-forward).

- **For:**
  - The WM keeps one way in: a Trezor-signed advance in the current session.
  - The Trezor checks every step itself, and a hostile WM cannot sign a history the wallet never
    made.
  - The re-signed steps are bound to a session like any other authorization, so they expire with it.
- **Against:**
  - A Trezor must be connected, ahead of the restored WM, and the user must approve.
  - Each step costs a MAC check, a WM signature check and a new signature on the device.
  - The deprecated service channel does not support it.

### Option B: the WM accepts its own records directly (not implemented)

The host presents the WM's acceptance records to the WM. The WM verifies its own signature over
each step, compare-and-swaps on its head, and installs the step. No Trezor is involved.

- **For:**
  - It works while no Trezor is connected.
  - It is cheap: one signature check per step, on the WM.
- **Against:**
  - The WM gains a second way in that bypasses the Trezor. A WM bug or key compromise there is
    not checked by any wallet MAC.
  - Anyone holding the records can drive the WM forward with no device present, which widens the
    prefix choice below.
  - The records are not bound to any session, so they never expire.

### What both options leave open

Whoever holds the records chooses how far the WM is replayed, and after two restores also which
branch. The WM then attests an old genuine head as current. This is an accepted gap. See
[WM restore and roll-forward](gaps.md#wm-restore-and-roll-forward).

## The optional session field

The advance request may carry `session`: the nonce the host believes the WM holds. It is
**diagnostics only**. The WM always verifies the signature against the nonce it holds and never
trusts the field. When verification fails and the named session differs from the WM's, the
refusal says that the session it names has ended. A host can then sync and ask the Trezor again,
rather than treat the refusal as a forgery. wardd sends the nonce of the latest attestation it
obtained.

## Alternative: transitions without `from`

Two variants remove the `from` end. Neither is used.

### Omitting `from` from the advance request only

The Trezor still signs `from_counter` and `from_root`. The WM substitutes its own head when it
verifies, so a transition built on another head fails verification. The compare-and-swap becomes
implicit.

- **Security:** unchanged. The signature still commits to the predecessor.
- **Drawbacks:**
  - A stale head and a forged signature produce the same refusal. The WM has to return its head
    counter so the host can tell the two apart.
  - The links, attestations, acceptance records and `WardRollForward` still carry `from`. Only
    the advance request shrinks, by 36 bytes.

### Omitting `from` from the signature

The Trezor would sign only `(to_counter, to_root, session)`. The WM would have to infer where a
transition starts.

- **A batch passes the counter check.** In one session the Trezor can authorize H to A at c+1
  and a batch H to B at c+3; a host can hold the first back. After A lands, "to_counter above the
  head" accepts B. B lacks A's change, so the WM forks and silently loses A after signing its
  acceptance.
- **Two roots at one counter.** After a restore, the WM can hold (c, R_wm) while a Trezor holds
  (c, R_dev). The Trezor latches the attestation's nonce before it refuses the head, so it could
  authorize a write from (c, R_dev). Without `from_root` in the signature, the WM would accept it
  on a tree it does not hold.
- **Closing these.** Signing `from_counter` alone, plus a Trezor rule to mint only from the head
  its latched attestation names, would close both. That saves 32 bytes, adds an invariant every
  minting path must keep, and splits the preimage from `auth_commit`'s, which needs `from` for the
  chain walk.
