# WARD Manager

The WARD Manager (WM) orders each wallet's WARD transitions and attests which head is current. It
is an authority on freshness and ordering only. It sees roots in the clear and never sees an
entry. The Trezor accepts a head only after proving that it descends from its own head through
authorized links. Transitions, signatures, and sessions are described in
[transitions and sessions](ward_transitions.md).

## State

For each wallet the WM holds:

- **The register.** The step that reached the head, `(from_counter, from_root) ->
  (counter, root)`. It is durable and is restored from backups. It holds no time and no history:
  only the current head's step.
- **The opening challenge.** A volatile 32-byte challenge. A Trezor signs it to open a session,
  and the WM replaces it when that session opens.
- **The session nonce.** The round nonce of the session a Trezor opened last. It is volatile: it
  is not persisted, backed up, or handed over in a failover. See
  [sessions](ward_transitions.md#sessions).

The WM keeps no time. It dates each signature with its own clock when it signs, and refuses a
timestamp supplied by a caller. When the WM accepted a step is therefore recorded only in the
acceptance an advance returns. wardd keeps that record, with the WM's signature, in the replica
([the records](ward_roll_forward.md#the-records)). Once the head moves on, wardd's records are
the only trace of the earlier steps and their times.

## Operations

| Operation | Input | Result |
| --- | --- | --- |
| Head | `ward_id` | The current head `(counter, root)`, or none. |
| Enroll | `root`, `head_init_sig` | The wallet's first head. Genesis only. |
| Challenge | `ward_id` | The current opening challenge. Available before enrollment, and reading it changes nothing. |
| Open | `nonce`, session proof | Verifies the proof under `ward_id` against the current challenge, replaces the challenge, and makes `nonce` the session nonce. Returns the attestation of the head's step under `nonce`, dated now. |
| Attest | `nonce` | The attestation of the head's step under `nonce`, dated now. Read-only: the session is unchanged. |
| Advance | a transition and its `wm_sig`, optionally the session the host believes is current | Whether it was a revert, and the acceptance: the WM-signed record of the step under the session nonce, dated at acceptance. |

An advance is refused in four cases:

- **Conflict:** its `from` end is not the current head (the predecessor check). The refusal
  names the head's counter, so the host can sync and try again.
- **No session:** no Trezor has opened a session for the wallet.
- **Not authorized:** the `wm_sig` does not verify against the session nonce. If the host named a
  different session, the refusal adds that this session has ended. The WM never verifies against
  the named session; see [the optional session field](ward_transitions.md#the-optional-session-field).
- **Out of range:** the transition does not advance the counter by 1 to 8.

An opening whose proof does not verify against the current challenge is refused, and the Trezor
syncs again. The session protocol is described in [sessions](ward_transitions.md#sessions).

The WM has one way in: a Trezor-signed advance in the current session. No operation installs a
step on the WM's own say.

## Roll-forward

A WM whose register goes back no longer holds steps it accepted: after a restored backup, a
failover onto a stale replica, or a lost register. Roll-forward returns it to its newest head. A
Trezor signs the accepted steps again for the current session, and wardd submits them as ordinary
advances, so the WM keeps its one way in. See [WARD roll-forward](ward_roll_forward.md).

## Obligations and open work

- **Sessions and challenges are volatile.** A restore or a failover must not bring back a session
  nonce or a challenge. A restored session would make that session's unlanded authorizations
  valid again, and a restored challenge would let a held opening proof reopen one. A WM with
  several instances must consume the challenge and replace the session in one serialized step per
  wallet, and fence a stale instance on failover.
- **The replay stops where the record holder chooses (accepted gap).** After a restore, whoever
  holds the records chooses how far the WM is replayed, and the WM then attests an old genuine
  head as current. Trezors whose stored counter is past that head refuse it by the counter floor.
  A fresh Trezor, or one that rarely syncs, accepts it. Preventing it would need a per-wallet
  high-water mark that a restore cannot take back, and no acceptable store for one exists. See
  [WM restore and roll-forward](gaps.md#wm-restore-and-roll-forward).
- **A wallet the WM lost entirely** has no head to roll onto. Re-enrollment needs the genesis
  `head_init_sig`, which only a Trezor at counter 0 supplies.
- **Durability.** The WM must not attest a head before it is durable. See
  [durable WM state](gaps.md#durable-wm-state).
- **The production WM** does not implement sessions or the optional session field yet.
