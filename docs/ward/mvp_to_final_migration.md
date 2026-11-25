# Migrating a WARD wallet from MVP to WARD Manager

Proposed design for upgrading an existing WARD wallet from the firmware and wardd builds
without a WARD Manager (WM) to a deployment with one. The ordinary upgrade runs on the first
WARD sync after the update. It keeps the existing entries, offline copies, and queued
changes. The user continues to use the same Trezor, passphrase, and WARD app.

## Starting point

The MVP device persists the head it reached by verifying its wallet's transition chain.
Evolu holds the sealed changes and transition history. The device also holds the local
queue and its reconciliation records. Both builds use the same wallet keys, leaf format,
and device-facing `auth_commit` for ordinary writes. Those parts can carry forward in place.
The MVP's public step signatures authorize storage by wardd. The final build's public
signatures authorize advances from a particular WM head, by a predecessor check.

The WM enrolls only at counter zero. The normal attestation verifier also expects a
counter advance above zero. Migration therefore needs a distinct enrollment operation
and a signed way to represent the imported checkpoint. See the [leaf format](ward_leaf_encryption.md)
and the [threat model](threat_model.md).

## Normal upgrade

1. The upgraded firmware recognizes the active wallet's locally persisted MVP head.
   The existing WARD session starts a migration round bound to that wallet. The device
   exposes the exact stored counter and root for this round.
2. wardd rebuilds that exact checkpoint from its existing log. It waits if the required
   rows are still replicating. It verifies that it can serve proofs from the checkpoint
   before asking the WM to enroll it.
3. The Trezor signs a dedicated migration authorization for the checkpoint. The WM
   verifies it against the wallet's public key and atomically creates the register if it
   is uninitialized. The verification key for the target WM comes from the firmware's
   trusted configuration. The WM dates its signatures with its own clock and stores no time.
4. The WM attests the checkpoint against a fresh device challenge. The Trezor verifies
   the attestation, checks that it matches the checkpoint it authorized, and records WM
   adoption. wardd pins the proof-serving view to that head for the session.
5. Normal WM sync and writes resume. The first WM-authorized write starts from the same
   root and counter and advances by a predecessor check on that head. The app keeps the usual
   confirmation flow for writes and conflicts.

The imported counter and root stay the same. No leaves are decrypted, re-encrypted, or
replayed as new writes. A pending change stays pending unless the device can prove that
its specific transition landed on the accepted chain.

## Required changes

| Component | Change |
| --- | --- |
| Firmware | Track the provenance of the stored head per wallet. Allow the migration round only for an eligible, locally persisted MVP head through the existing authorized WARD session. Add checkpoint attestation verification and persist WM adoption atomically with the head and its WM metadata. |
| Wire protocol | Add an explicit migration capability and messages for the checkpoint authorization and attestation. Bind the authorization to its purpose, the wallet, the target WM deployment, the exact counter and root, and a fresh enrollment challenge. Sign the checkpoint kind as part of the WM attestation. |
| WM | Add a one-time, transactional checkpoint enrollment to the production register. Store the enrollment origin; the WM stores no time, and wardd keeps the WM-signed record of the enrollment with its date. Make retries idempotent for the accepted origin. Preserve enrollment history across recovery so a lost register is not treated as a new wallet. |
| wardd | Extend `WmClient` and the existing sync path. Reuse Evolu, the trie, and proof serving. Materialize the candidate at the device's head and resume normal sync on retry. Keep the cached proof and the existing transition rows. |
| Release and clients | Coordinate firmware, wardd, and WM capabilities. Run migration as part of the normal reconnect or sync for supported clients. Preserve local records if any component is too old, and report that the upgrade is pending. |

For MVP firmware that has not shipped, persist an explicit MVP marker with the head now.
An absent timestamp is insufficient to identify the source of a head because older WM
records can also lack timestamps. For already deployed MVP firmware, establish eligibility
using trusted upgrade provenance for the supported builds. A normal host request must not
be able to label arbitrary device state as eligible. Define downgrade behavior before
release. A supported downgrade must preserve the WM adoption marker and refuse MVP writes
for that wallet, or the release must block that downgrade.

Keep normal genesis enrollment and ordinary WM transition attestations as separate cases.
An imported checkpoint certifies the head the WM took over. The older MVP links remain
wallet-authenticated history. A second device at an earlier head uses those links to
prove ancestry to the checkpoint, or through it to a later WM head. A replacement device
starting at genesis can do the same when the complete history is available. Preserve the
checkpoint attestation for offline catch-up and apply the normal WM freshness warning.

## Multi-device cutover

The supported automatic path starts with the current MVP writer and its replica. If an
MVP release permits multiple writers, or another host still runs MVP during cutover, there
can be authentic writes the migrating device has never seen. Neither the maximum counter
nor the WM can establish the user's intended branch retroactively.

- For an ordinary rollout, stop MVP publication at cutover and arrange for the existing
  writer to migrate first. A known MVP wallet racing with an empty or replacement device
  must go through the migration path before genesis enrollment can claim its register.
  Carry this admission information from the rollout or provisioning state. Without it,
  a blank device alone cannot distinguish a new wallet from an existing MVP wallet.
- A second device on the accepted chain catches up automatically once the required rows
  arrive. If it holds a divergent or unimported later history, preserve its rows and
  pending changes. Surface the conflict and let the user recover those changes before
  marking that device migrated. An atomic first enrollment keeps the WM head unique.
  It does not establish which of two disconnected MVP branches the user wanted.

## Failure handling and acceptance tests

- **Unchanged data.** Upgrade a wallet with writes, deletes, pointers, offline copies,
  and pending changes. Check the same root and counter immediately after import and
  verify reads. Flush the preserved queue once through the WM.
- **Interrupted upgrade.** Interrupt before WM enrollment, after enrollment but before
  the response, and after the response but before the device persists adoption. Every
  retry converges on the same enrollment and preserves the local state. Check what
  happens if the WM advances before the original device reconnects.
- **Missing rows.** A partial replica stays pending. It keeps the existing local records
  and resumes once it can serve the checkpoint. Check that the first post-upgrade read
  uses the adopted root even if replication has brought in a newer head.
- **Multiple devices.** Test an older device on the same chain, a replacement device, a
  fork, and a race between checkpoint import and genesis enrollment. The WM never
  replaces an existing enrollment with an import.
- **Trust boundary.** Reject another wallet's authorization, the wrong WM deployment,
  an altered checkpoint, expired enrollment challenges, and attempts to migrate a
  wallet that already adopted WM state. Test that a register restore cannot reopen
  enrollment for that wallet.

Migration preserves the MVP head the device already trusts and starts WM ordering from
there. Its guarantee begins at checkpoint acceptance. Any release that promises a
seamless upgrade for every MVP wallet must control the single-writer cutover or define
how conflicting branches will be preserved and recovered.
