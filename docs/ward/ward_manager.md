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
- **The session nonce.** The round nonce of the session a Trezor opened last. It is volatile: it is not
  persisted, backed up, or handed over in a failover. See
  [sessions](ward_transitions.md#sessions).

The WM keeps no time. It dates each signature with its own clock when it signs, and refuses a
timestamp supplied by a caller. When the WM accepted a step is therefore recorded only in the
acceptance that `advance` returns. wardd keeps that record, with the WM's signature, in Evolu
([the records](ward_roll_forward.md#the-records)). Once the head moves on, wardd's records are the only trace of the
earlier steps and their times.

## API

The development WM serves this over HTTP (`packages/wardd/src/wmServer.ts`, started by
`wmCli.ts`). wardd talks to it through `HttpWm`, or uses the in-process `DevWm`
(`packages/ward-core/src/wm.ts`). The firmware tests emulate it as `MockWM`
(`tests/ward_wm.py`). Bytes travel as hex, and an absent root as `null`.

| Route | Request | Result |
| --- | --- | --- |
| `GET /v1/info` | | `{pubkey}` |
| `GET /v1/wards/{ward_id}/head` | | `{head: {counter, root} \| null}` |
| `POST …/enrol` | `{root, headInitSig}` | `{}`. Genesis only. |
| `GET …/challenge` | | `{challenge}`. Available before enrollment. |
| `POST …/open` | `{nonce, proof}` | The attestation of the head's step under `nonce`, dated now. Verifies the proof under `ward_id` against the current challenge, replaces the challenge, and makes `nonce` the session nonce. Enrolled wallets only. |
| `POST …/attest` | `{nonce}` | The attestation of the head's step under `nonce`, dated now. Read-only: the session is unchanged. |
| `POST …/advance` | `{fromCounter, fromRoot, toCounter, toRoot, wmSig, session?}` | `{revert, acceptance}`. `acceptance` is the WM-signed record of the step under the session nonce, with that `nonce`, dated at acceptance. `session` is diagnostics only. |

`open` refuses a proof that does not verify against the current challenge with `403` "invalid or
expired session proof; sync again". The session protocol is described in
[sessions](ward_transitions.md#sessions).

A refused predecessor check returns `409 {error: "conflict", headCounter}`. `advance` fails with
"no session" when the wallet has no session nonce, and with "not authorised" when `wmSig` does not
verify against it. If the request names a `session` that differs from the WM's, the refusal adds
that the session it names has ended. The WM never verifies against the named session; see
[the optional session field](ward_transitions.md#the-optional-session-field).

The WM has one way in: a Trezor-signed advance in the current session. It has no route that
installs a step on its own say.

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
  `head_init_sig`, which only a Trezor at counter 0 supplies today.
- **The development WM's durability** is still open. See
  [durable WM state](gaps.md#durable-wm-state).
- **trezor-suite-sync's `wardManager`** does not implement sessions or the optional `session`
  field yet.
