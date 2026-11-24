# WARD security gaps

This review covers firmware and Suite `petrsusil/ward-draft` through firmware
`0271e08ab5` and Suite `8f2830e585`, plus the fixes described below. It follows the
[WARD threat model](threat_model.md). The Trezor is responsible for wallet authentication
and user consent. wardd, the relay, and a replica peer can fail or supply misleading
data. With a WM, ordering and live freshness depend on a trusted, durable register.

## Summary

| Priority | Finding | Status |
| --- | --- | --- |
| P1 | Connect forwards device calls outside the WARD conversation. | Open |
| P1 | Opening a replica sent the parent Evolu credential to wardd. | Fixed in relay v2 |
| P1 | The public write signature leaves the chain MAC outside its scope. | Open |
| P1 | The development WM can attest a head before committing it to disk. | Open |
| P1 | Rollback could approve a root with no historical proof. | Fixed in firmware |
| P1 | The MVP flash keys overlap records from public mini-WARD. | Open |
| P2 | Cached catch-up can accept an ambiguous timestamp or serve proofs from the wrong head. | Open |
| P2 | Malformed rows can block replay of otherwise healthy history. | Open |
| P2 | Two device display paths bypass the intended reveal policy. | Open |
| P2 | Queued writes can miss intervening changes, and adoption and settlement can be interrupted. | Open |
| P2 | Relay waits could hold the wallet lock and service catch-up could exceed the wire buffer. | Fixed |
| P2 | Service catch-up could need a daemon restart after a dropped page. | Fixed in service v3 |
| P2 | Large replica rebuilds and disconnected queued calls still consume wallet time. | Open, characterized by tests |

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

Give each relay operation an allowlist and enforce the conversation phase, including
which pull acknowledgment is expected. Apply the check before invoking a device
command, and bind the endpoint to the installation's trusted daemon. The Python
[binding](../../python/src/trezorlib/ward_relay.py) already restricts message names.
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

The device's public signature commits to both heads and, in WM mode, the head
nonce. wardd stores `auth_commit` for subsequent device chain verification. Today
it can accept a result with a genuine public signature and a damaged chain MAC. It
can then advance the WM to a root whose stored inbound link the Trezor refuses.
Firmware verifies the chain MAC and rejects that history, so the direct consequence
is recovery or sync failure.

Version the public step signature to commit to the chain MAC in both deployments.
Include the accepted link identity in the WM attestation so the hardware and replica
agree on the occurrence used for settlement. Check old rows explicitly during
migration. Test serialization and verification across firmware and hosts, including
repeated roots, reverts, and an unusable row beside a healthy chain.

### Durable WM state

The development WM updates the in-memory head before its file write finishes.
An attestation can observe that change while persistence is still pending. An
older snapshot also carries its older nonce-retirement ledger, so restoring both
together can make a superseded head nonce current again.

Publish a head to readers and sign it only from committed state. Keep advance and
initial enrollment transactional and make the outcome queryable after an uncertain
response. Track nonce retirement or a signed recovery generation in state that
survives register restore. Exercise disk failure, process interruption, concurrent
attestation, and restoration of an earlier register.

### Verified rollback

[`WardRollback`](../../core/src/apps/ward/rollback.py) now checks the proposed counter
and root before showing the hold screen. For normal rollback, the device walks back
from the live WM-attested head. If the WM has regressed, the device establishes that
the WM head is an ancestor of its own stored head, then proves the target from the
device's history. That still permits restoring the device's own stored root without
discarding changes. A branch switch belongs in the separate rejoin flow.

The device checks both checkpoints during one backward walk. The live attestation
identifies the newest WM transition, and archived WM attestations link older
transitions by their head nonces. The device stores its adopted nonce with its root
and counter. Devices with older root records must sync once to record that nonce.
When the WM has regressed and minted a fresh nonce, the restored counter and root
must be on the history anchored to the occurrence the device stored. At a non-genesis
restored head, the WM must retain the consumed predecessor nonce from its backup
so the device can identify the original step.

The screen distinguishes the current device state, current WM state, verified target
counter, and new transition counter. It shows how many changes followed the target.
The revert continues to extend the WM head and quote its live nonce. A host that
lost the chain evidence must recover it from another replica or backup before using
this flow. Arbitrary reconstruction from surviving leaves would require a separately
designed recovery operation and a different user decision.

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

The WM is the only source of acceptance time. Firmware rejects a cached attestation
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
still abort the entire operation before that check. Unvalidated counter progression
also weakens the traversal bound. Validate each row before indexing it and isolate
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
The service daemon and device firmware must both support service protocol v3.

The daemon still rebuilds its replica before serving a chain, and predecessor
selection scans the transition log once per link. Queued catch-up still rebuilds
before it discovers that its caller disconnected. Tests characterize both costs
without relying on wall-clock timing.
