# WARD Manager

The WARD Manager (WM) orders each wallet's WARD transitions and attests which head is current. It
is an authority on freshness and ordering only. It sees roots in the clear and never sees an
entry. The Trezor accepts a head only after proving that it descends from its own head through
authorized links. Transitions, signatures, and sessions are described in
[transitions and sessions](ward_transitions.md).

## State

For each wallet the WM holds:

- **The register.** The step that reached the head, `(from_counter, from_root) ->
  (counter, root)`, and the WM's acceptance timestamp. It is durable and is restored from backups.
- **The session nonce.** The round nonce of the wallet's latest sync. It is volatile: it is not
  persisted, backed up, or handed over in a failover. See
  [sessions](ward_transitions.md#sessions).

The WM assigns every timestamp itself and refuses one supplied by a caller.

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
| `POST …/attest` | `{nonce}` | The attestation of the head's step. The nonce becomes the session nonce. |
| `POST …/advance` | `{fromCounter, fromRoot, toCounter, toRoot, wmSig, session?}` | `{revert, acceptance}`. `acceptance` is the WM-signed record of the step under the session nonce, with that `nonce`. `session` is diagnostics only. |

A refused compare-and-swap returns `409 {error: "conflict", headCounter}`. `advance` fails with
"no session" when the wallet has no session nonce, and with "not authorised" when `wmSig` does not
verify against it. If the request names a `session` that differs from the WM's, the refusal adds
that the session it names has ended. The WM never verifies against the named session; see
[the optional session field](ward_transitions.md#the-optional-session-field).

The WM has one way in: a Trezor-signed advance in the current session. It has no route that
installs a step on its own say.

## Roll-forward

A WM whose register goes back no longer holds steps it accepted. That happens after a restored
backup, a failover onto a stale replica, or a lost register. Roll-forward returns it to its newest
head. The Trezor signs the accepted steps again for the current session, and wardd submits them as
ordinary advances. [Transitions and sessions](ward_transitions.md#roll-forward) explains why the
stored signatures cannot be reused, and compares this with letting the WM accept its own records
directly.

### The records

A WM record is any attestation the WM signed for exactly that step:

- **The acceptance from `advance`.** It is signed under the session nonce.
- **An attestation from a later sync.** It is signed under that sync's nonce, while the step was
  the head.

wardd keeps one verified record per step (`StoredAttestation`, replicated through Evolu with the
links). The newest record replaces an older one for the same step.

### What wardd does

`WardHost.rollForward` in `packages/wardd/src/host.ts` runs during a sync on the wallet channel,
when the Trezor answers `WardIngestAttestation` with `wm_behind`, so the Trezor detects the
restore and not wardd:

1. Take the verified kept records whose `to_counter` is above the WM's head, newest first.
2. For each, walk the replica's links back from its head. The WM's current head must lie on that
   walk. If no candidate's walk passes through it, the WM is on another branch, which is a rejoin
   case, and nothing is replayed. The walk is bounded by the counter distance.
3. Use the path up to the first step without a kept record.
4. Send the path to the Trezor in pages of 16, in `WardRollForward`, with the WM's live
   attestation and each step's record, marking the last page `final`. The user approves on the
   first page; on the last, the Trezor shows when the WM accepted the last restored change.
5. Submit each returned signature to the WM with `advance`, naming the round nonce as the
   diagnostic `session`, and keep each acceptance.
6. Before the next page, attest again under the same round nonce, because the Trezor's round is
   still open. That anchors the next page on the advanced head.
7. When done, attest once more, ingest it, and continue the normal sync, where the Trezor now
   reconciles. The sync result carries `rolledForward: {steps, toCounter, lastTimestamp}`.

A refusal by the Trezor or the WM, or a declined approval, ends the roll-forward there, and a
Trezor still ahead of the WM then fails the sync with `wm_behind`. A Trezor that is not ahead of
the restored WM, such as a fresh one, does not detect the restore and adopts the WM's head as
usual. `--no-roll-forward` (`rollForward: false`) turns
roll-forward off. The deprecated service channel does not roll forward.

The Trezor's checks are listed under
[option A](ward_transitions.md#option-a-the-trezor-signs-the-transitions-again-implemented): its
own MAC, the WM's signature, contiguity from the attested head, and agreement with its own head.
Tests: the `test_ward_roll_forward_*` and `test_ward_attack_roll_forward_*` device tests, the
wardd tests in the "a WM whose register went back" group of `host.test.ts`, and the mock WM tests
in `tests/test_ward_wm.py`.

## Obligations and open work

- **Sessions are volatile.** A restore or a failover must not bring back a session nonce. A
  restored session would make that session's unlanded authorizations valid again.
- **The replay stops where the record holder chooses.** After a restore, whoever holds the
  records chooses how far the WM is replayed, and the WM then attests an old genuine head as
  current. Trezors whose stored counter is past that head refuse it by the counter floor. A fresh
  Trezor, or one that rarely syncs, accepts it. The fix is open:
  - Keep a per-wallet high-water mark outside the backup: the highest counter and timestamp the WM
    ever attested.
  - After a restore, enter recovery mode. Accept an advance only together with the WM's own record
    of that exact step, and attest no head as current until the head reaches the high-water mark.
    Roll-forward advances already come with their records, so wardd would send them along.
  - Leave recovery without reaching the mark only by an operator decision. Trezors then need the
    rejoin flow.

  Recovery mode also closes the [reopened nonce](ward_transitions.md#what-a-session-does-not-prevent).
- **A wallet the WM lost entirely** has no head to roll onto. Re-enrollment needs the genesis
  `head_init_sig`, which only a Trezor at counter 0 supplies today.
- **The development WM's durability** is still open. See
  [durable WM state](gaps.md#durable-wm-state).
- **trezor-suite-sync's `wardManager`** does not implement sessions or the optional `session`
  field yet.
