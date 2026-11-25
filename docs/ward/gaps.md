# WARD security gaps

This review includes the session-bound WM and roll-forward changes through firmware
`2e4f35c7d2` and Suite `299d49287e`, and the session activation fix described below.
It follows the [WARD threat model](threat_model.md). The Trezor is responsible for wallet authentication
and user consent. wardd, the relay, and a replica peer can fail or supply misleading
data. With a WM, ordering and live freshness depend on a trusted, durable register.

## Summary

| Priority | Finding | Status |
| --- | --- | --- |
| P1 | Connect forwards device calls outside the WARD conversation. | Open |
| P1 | Opening a replica sent the parent Evolu credential to wardd. | Fixed in relay v2 |
| P1 | The public write signature leaves the chain MAC outside its scope. | Open |
| P1 | The development WM can attest a head before committing it to disk. | Open |
| P1 | A head attestation could reactivate a retired write authorization or interrupt the current writer. | Fixed by authenticated session activation |
| P1 | After a WM restore, the holder of the records chooses how far it is replayed. | Accepted |
| P1 | The device can report a label as current after detecting WM regression. | Open |
| P1 | Recovery can publish a head whose encrypted leaves the replica cannot serve. | Open |
| P1 | Rollback could approve a root with no historical proof. | Fixed in firmware |
| P1 | The MVP flash keys overlap records from public mini-WARD. | Open |
| P2 | Roll-forward approval covers the first page and completion precedes WM confirmation. | Open |
| P2 | Missing or incompatible receipts can strand recovery after a successful write or upgrade. | Open |
| P2 | Replaying a step can replace its original acceptance date in the recovery display. | Open |
| P2 | Rust and Java relay clients refuse roll-forward. | Open |
| P2 | Cached catch-up can accept an ambiguous timestamp or serve proofs from the wrong head. | Open |
| P2 | Malformed or cyclic rows can block or hang replay of otherwise healthy history. | Open |
| P2 | Two device display paths bypass the intended reveal policy. | Open |
| P2 | Queued writes can miss intervening changes, and adoption and settlement can be interrupted. | Open |
| P2 | Relay waits could hold the wallet lock and service catch-up could exceed the wire buffer. | Bounded and fixed |
| P2 | Service catch-up could need a daemon restart after a dropped page. | Fixed in service v3 |
| P2 | Large replica rebuilds and disconnected queued calls still consume wallet time. | Open, characterized by tests |
| P2 | Rollback verifies one WM signature per historical link. | Open |

Before distributing the MVP, close the Connect boundary and write-signature gaps and
make the public mini-WARD upgrade preserve its flash records. MVP avoids a dependency
on a WM and still relies on an authenticated chain from a device's stored head. It
needs a controlled single-writer cutover for automatic migration.

Before distributing the WM build, provision the production verification key and a
compatible durable register. The release key in [firmware](../../core/src/apps/ward/attest.py)
is a placeholder, so release verification currently fails closed. Test both migrations,
including interruption and divergent histories, under the production trust configuration.

## Deep dive

### Connect relay permissions

`wardRelay` accepts a caller-supplied endpoint. `DeviceCurrentSession.relayCall()`
checks the protobuf schema and lets the peer choose which recognized firmware
message to send. Connect grants permission for a WARD operation. A generic firmware
schema is wider than that permission. Device authorization and confirmations still
apply, but they do not enforce the Connect method boundary.

Since relay v2, `openStore` also sends the WARD owner secret to that caller-supplied
endpoint, so the endpoint choice is a credential exposure as well as a permission gap.

Give each relay operation an allowlist and enforce the conversation phase, including
which pull acknowledgment is expected. Apply the check before invoking a device
command, and bind the endpoint to the installation's trusted daemon. The Python
[binding](../../python/src/trezorlib/ward_relay.py) already restricts message names, but
it does not check the phase, and it checks only the `ws` scheme, not that the host is local.
Verify that ordinary sync, catch-up, and batch flush still work and that out-of-scope
messages never reach the transport.

### Evolu credential scope

Previously, relay `openStore` sent the full node returned by `EvoluGetNode` to the
daemon. That node carries access beyond the WARD replica. The device-message logger
also lacked redaction for that response.

Relay v2 sends the 32-byte WARD owner secret. Connect, Python, Rust, and Java derive
the same SLIP-21 child before opening the store. The existing WARD owner and its
replicated rows stay usable. The server rejects the legacy parent field, and the
version handshake requires upgraded clients. Connect redacts the node and its
delegation proof. The WARD owner secret still authorizes replica access, so trusted
endpoint selection from the previous finding remains relevant. Existing copies of
the parent credential in a daemon or old logs are outside the scope of this fix.

### Transition authorization and chain data

The device's public signature commits to both heads. wardd stores `auth_commit` for subsequent device chain verification. Today
it can accept a result with a genuine public signature and a damaged chain MAC. It
can then advance the WM to a root whose stored inbound link the Trezor refuses.
Firmware verifies the chain MAC and rejects that history, so the direct consequence
is recovery or sync failure. The failure outlives the faulty daemon: the WM's head is
global, so every honest replica is stranded on a head whose inbound link no device
accepts, and replacing wardd does not repair it.

Version the public step signature to commit to the chain MAC in both deployments.
Include the accepted link identity in the WM attestation so the hardware and replica
agree on the transition used for settlement. Check old rows explicitly during
migration. Test serialization and verification across firmware and hosts, including
repeated roots, reverts, and an unusable row beside a healthy chain.

### Durable WM state

The development WM (`packages/wardd/src/wmServer.ts` around `DevWm`) updates the
in-memory head before its file write finishes. An attestation can observe that change
while persistence is still pending. If the write fails, the head stays advanced in
memory while the writer receives a refusal, so the writer and later readers disagree
about whether the step landed.

Publish a head to readers and sign it only from committed state. Keep advance and
initial enrollment transactional and make the outcome queryable after an uncertain
response. Exercise disk failure, process interruption, concurrent attestation, and
restoration of an earlier register. Restoration is the subject of the next section.

### WM restore and roll-forward

The WM holds no head nonce. A Trezor's `wm_sig` covers the transition and the session
nonce: the round nonce the Trezor authenticated with the WM's single-use challenge.
The WM keeps the nonce of the wallet's latest authenticated session and accepts an advance only when it is bound to that nonce
and starts at its head. After accepting, it signs its own record of the step under the
session nonce. See [transitions and sessions](ward_transitions.md).

A restored backup, a failover onto a stale replica, or a re-enrollment after total loss
makes the register go back. The session nonce is volatile, so a restore ends every
session, and the restored WM accepts none of the stored `wm_sig`s. That includes lost
races and publications a host held back. What the WM had accepted comes back by
roll-forward. wardd feeds a Trezor the accepted steps with the WM's record of each. The
Trezor checks its own MAC and the WM's signature, and signs each step again for the
current session (`WardRollForward`). wardd then submits the new signatures as ordinary
advances. A step with no WM record cannot come back. See
[roll-forward](ward_transitions.md#roll-forward), which also covers the alternative of
the WM accepting its own records directly.

The following **accepted gap** concerns recovery after the register goes back.

- **Prefix choice.** Whoever holds the records chooses how far a restored WM is
  replayed. That includes wardd, a replica peer with the WARD owner secret, and old
  logs. After two restores, two branches can grow from one head, and that holder also
  chooses the branch. The WM then attests an old genuine state as current. Trezors
  whose stored counter is past it refuse it by the counter floor. A fresh Trezor, a
  restored seed, or a rarely synced Trezor accepts it, shows stale data, and may write
  on top, which forks the history. Nothing can be forged, and a malicious WM could
  already present any genuine historical state. The difference is that an honest WM
  can now be steered by a host after a restore.

Preventing prefix choice requires an independent per-wallet high-water mark and a recovery
mode that withholds live attestation until the register reaches it. The mark would have
to live where a restore, a failover onto a stale replica, and a total loss of the WM's
storage cannot take it back. No acceptable store exists:

- **wardd or the replica.** These hold the records and choose the prefix, so they are
  the parties the mark defends against. They can withhold it.
- **A separate store run by the WM operator.** It goes back together with the register
  in an operator-driven or botched restore, so it adds a second durable dependency
  without an independent guarantee.
- **An HSM monotonic counter beside `K_sig`.** It ties every wallet's state to signing
  hardware and does not survive the loss of that hardware.
- **External witnesses or a transparency log.** They add parties outside the WARD trust
  model and a round trip to every attestation.

The design therefore relies on a restore being rare and on these bounds: nothing is
forged, every step that lands is one a Trezor authorized, and a Trezor never goes below
its stored counter without a separately approved demotion.
`test_a_restored_wm_can_be_stopped_at_any_prefix` in `tests/test_ward_wm.py` records this limit.

A WM that lost the wallet entirely holds no head to replay onto. Re-enrollment needs the
genesis `head_init_sig`, which only a Trezor at counter 0 supplies today. A re-enrollment
at genesis, two competing branches, and a write racing the replay remain open.

### Authenticated write sessions

Previously, asking for a head attestation changed the active session. A host could revive
a held write at an unchanged predecessor even during ordinary operation. Anyone able to
request attestations for that wallet could also interrupt its current writer.

The development WM now requires a device signature over the wallet ID, its current
32-byte challenge and the fresh nonce generated by the Trezor. It consumes the challenge
and replaces the session in one operation. Head and challenge reads have no effect on
the active writer. Restart and restore start with fresh challenges. The device, wardd
and WM must support this handshake together. A production WM with multiple instances
must serialize challenge consumption and session replacement per wallet and fence stale
instances on failover. The MVP has no WM session.

### Freshness after detected regression

On the Connect channel a previously online device can ingest an authenticated lower WM
counter and report `wm_behind` while the earlier online flag remains set. If recovery is
declined or interrupted, a label proven against the stored root can still say “Label proven
current.” Clear the online flag and the earlier adoptable attestation on detection. Restore
freshness only after adoption. Verify the label and write paths before and after an
interrupted recovery in the same device session.

### Recoverable data before publication

wardd materializes the restored WM head, then selects later links by their endpoints and
verified receipts. Roll-forward checks their MACs and signatures. Neither check establishes
that the recovering replica still has the encrypted leaf changes needed to serve those later
roots. Before requesting signatures, apply the entire proposed path to a single snapshot and
check each resulting root. Report the first unavailable transition before publishing any step.
Cover a valid receipt and MAC paired with a damaged or missing leaf change.

### Roll-forward consent and completion

The first approval counts the changes on that page. Later pages reuse approval, and the
device may release signatures before the path reaches its own stored checkpoint. The final
screen announces restoration before wardd submits those signatures. Bind approval to the
intended counter and root, prove the path through the device checkpoint before releasing
signatures, and show completion only after a fresh attestation of the approved target.
Cover page boundaries, a declined later page, and a disconnect before the final publication.

### Receipt durability and upgrade

wardd logs a receipt append failure and can still acknowledge publication. The WM exposes
only its current step. Once it moves again, an unavailable historical receipt can stop
roll-forward and deep rollback. Report WM acceptance and durable receipt storage separately,
and support idempotent receipt retrieval by transition after a lost response or failed append.
Test recovery after another writer has already advanced.

The previous draft's v6 receipts fail current v7 verification. An intact Evolu archive can
therefore lose its historical proof coverage on upgrade. Provide versioned historical
verification or an authenticated migration checkpoint and state the recovery range it covers.
Test an upgrade from populated v6 history, including interruption and a subsequent WM restore.

### Recovery dates

The WM keeps no time and dates each signature when it signs, so a replayed advance is dated
at reacceptance. wardd keeps only the newest record per step, so after a replay the original
acceptance record is gone, and a later restore shows the replay time as "Last confirmed".
That is true (the WM vouched for the step then) but hides when the change was first accepted.
Keep the original acceptance record alongside the newest one, and show both if the difference
matters. Exercise two restores of the same step. All authoritative times still come from the
WM's signatures, which only wardd stores.

### Recovery through relay clients

Python permits `WardRollForward`. The Rust and Java relay allowlists omit it, so a wallet
that syncs normally through either binding can lose its recovery path when the WM regresses.
Permit the request specifically in the recovery phase and run a restored-wallet sync through
each client, preserving rejection of unrelated device messages.

### Verified rollback

[`WardRollback`](../../core/src/apps/ward/rollback.py) now checks the proposed counter
and root before showing the hold screen. For normal rollback, the device walks back
from the live WM-attested head. If the WM has regressed, the device establishes that
the WM head is an ancestor of its own stored head, then proves the target from the
device's history. The target may also be the device's own stored root, which then
discards no changes; this is intended. A branch switch belongs in the separate rejoin flow.

The device checks both checkpoints during one backward walk. The live attestation
identifies the newest WM transition. Every older link must carry the WM's archived
attestation of that exact step, verified over the link's own `(counter, root)` ends.
The device asks for these with `WardChainRequest.with_acceptance`. When the WM has
regressed, the link into the WM's restored head must start at the predecessor named
by the WM's live attestation. A pair repeats only if the register went back, so the
receipt chain is unambiguous within one register history; see the previous section.

The screen distinguishes the current device state, current WM state, verified target
counter, and new transition counter. It shows how many changes followed the target.
The revert extends the WM head, and the WM accepts it only by a predecessor check on that
head. A host that lost the chain evidence must recover it from another replica or
backup before using this flow. Rolling a restored WM forward (previous section) avoids
the regressed case altogether.

The device verifies one Ed25519 signature per historical link. The host sends 16 links
with receipts per page, which fits the 8704-byte buffer. The cost grows with the
distance to the target and nothing else bounds it. Measure a deep rollback on hardware
and decide whether to cap the distance. The firmware's per-page bound of 128 and its
"~77 links" comment predate receipts. Arbitrary reconstruction from surviving leaves
would require a separately designed recovery operation and a different user decision.

### mini-WARD layout and migration

Public mini-WARD and the MVP use the same protected flash namespace. The MVP
assigns roots, role pins, and settings to keys that may already hold version-0
records. An upgrade can therefore corrupt data before an app attempts to read or
copy it. Reserve the legacy keys and use a disjoint MVP layout before the first
boot that can write it. Run tests from real populated legacy storage, including
supported passphrases and a full store. See [mini-WARD to MVP](miniscript_to_mvp.md).

The [MVP-to-WM checkpoint design](mvp_to_final_migration.md) needs trusted provenance,
one-time enrollment, and durable adoption state. A valid MVP link proves what a
wallet device authorized. Global ordering begins at the imported checkpoint. Keep
old rows and pending changes when branches diverge, and decide how to admit known
MVP wallets before an empty device can enroll the same wallet at genesis.

### Cached catch-up and proof views

The WM's signatures are the only source of time. Firmware rejects a cached attestation
with a timestamp below the persisted floor, while equal timestamps remain eligible.
A one-second clock and register restore mean a signed time cannot establish a strict
recovery order. Use a signed recovery generation that survives restore. Keep time
for the freshness notice.

Separately, wardd can offer a cached head below its replica tip, then use the tip to
answer the next entry request. The device checks the proof against the head it
accepted and refuses the mismatch. Bind both reads and write preparation to the
device session's accepted root. Extend the existing below-tip catch-up test through
a successful read, with a newer replica value present.

### Replica validation and replay

The replica recovers from some root mismatches. Malformed JSON or link fields can
still abort the entire operation before that check. Counter progression is not
validated, and the replica walks with an unbounded limit (`Number.MAX_SAFE_INTEGER`),
so a self-loop or a two-row cycle from a replica peer makes the walk loop while it
holds the wallet lock. Validate each row before indexing it and isolate
failures. Check widths, operation shape, counter progression, and the public MVP
signature on replicated MVP links. Bound every walk and compare the rebuilt root
before serving data. Test a healthy history alongside bad rows and ensure the
wallet remains usable.

### Display-time authorization

[`DisplayAddress`](../../core/src/apps/display_address/show.py) resolves a label in
a domain supplied by the host, outside the WARD app-role filter. The v1
[reveal filter](../../core/src/apps/ward/app_role.py) also excludes flush, while a flush
conflict can show the published value before confirmation. Both affect what can be
shown on the device screen. Apply the role or reveal policy where stored plaintext
is about to be shown. Show an address without a WARD label when the caller lacks
authorization, and ask before revealing the conflicting value on v1.

### Queued changes and crash consistency

[`flush_queue`](../../core/src/apps/ward/flush_queue.py) treats proven absence as safe
to overwrite and uses the leaf's original write counter to judge other conflicts.
A subsequent deletion yields an absence. A revert can restore a value stamped
before the queued intent even though the effective value changed afterward.
Record the entry state proven when the user queued the intent, where available, and
ask if intervening history leaves the result ambiguous.

[`adopt`](../../core/src/apps/ward/adopt.py) settles claims before the new root is
persisted. Interruption can leave a queued change marked settled while the old root
remains in flash. Journal the adoption and its settlement together or make settlement
recoverable from the committed root and the verified links. Test reboots at each
storage boundary, including batches and an offered change replaced by a newer intent.

### Relay and service availability

wardd allows two minutes for an individual device reply and fifteen minutes from the
first device request. On expiry it rejects the pending reply and closes the socket.
The wallet lock is released as the conversation unwinds. If a publication already
landed, the next sync resolves its outcome.

The service sends one WM attestation and lets the device pull up to 64 links
per response. Each page fits the [codec buffer](../../core/src/trezor/wire/buffers.py).
The device walks backward from the attested step to its exact stored counter and root
before adopting, and keeps only the verified commitments needed for its pending
claims. Service protocol v3 adds idle binding renewal to the codec daemon. A retry
after a dropped page starts a fresh sync once the device receives a renewal.
The service daemon and device firmware must speak the same service protocol version, which
the device checks for an exact match. Version 3 added idle binding renewal; the current
version 4 removed the WM head nonce. Only
the device checks the version: `WardServiceOpenAck` carries none, and wardd learns of a
mismatch only from the refusal. Some proto comments still say v2.

The daemon still rebuilds its replica before serving a chain, and predecessor
selection scans the transition log once per link. Queued catch-up still rebuilds
before it discovers that its caller disconnected. Tests characterize both costs
without relying on wall-clock timing.
