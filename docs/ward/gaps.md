# WARD security gaps

The [threat model](threat_model.md#accepted-security-limitations) records the accepted limits on
freshness, application authority, manager durability and recovery completeness.

## Access and display

- **Local service access.** The pairing token grants access to the whole service. Another
  authenticated client can reuse an open wallet store without presenting its replica credential.
- **On-device disclosure.** Standalone address display can request a label outside the WARD
  application role. On transports without host identity, a queue conflict can display a stored
  value before the user approves revealing it.

## Publication and reads

- **Chain evidence.** A public write signature covers the two heads. A manager can accept the
  transition even if its replica holds a damaged wallet authentication tag. Devices that need
  that tag to verify history can then be unable to sync.
- **Cached reads.** Signed timestamps can tie. A replica can also serve a proof from a newer head
  than the cached one the device selected. The device refuses the proof.
- **Queued changes.** A deletion removes the leaf's write counter, and a revert can restore an
  older counter. Both can hide an intervening edit. Interruption between settling a queued change
  and saving the adopted head can also leave the two inconsistent.

## Recovery and availability

- **Missing data.** Recovery can reauthorize a head whose encrypted entries the replica can no
  longer reconstruct. A lost response, failed receipt save or incompatible older receipt can
  also leave a previously accepted step unavailable for replay.
- **Recovery date.** After replay, the available receipt may show when the manager last confirmed
  a step rather than when it first accepted it.
- **Client support.** The Rust and Java relay integrations and the dedicated service channel lack
  roll-forward. Deep rollback requires historical evidence and verification for every step traversed.
  The [recovery flow](ward_roll_forward.md#what-the-user-approves) describes the scope of user approval.
- **Replica availability.** Malformed records can block reconstruction. Device reply deadlines
  bound stalled relay exchanges, while a large rebuild can still occupy the service for that wallet.

Upgrade-specific risks are described in the proposals for [mini-WARD import](miniscript_to_mvp.md)
and [manager enrollment](mvp_to_final_migration.md).
