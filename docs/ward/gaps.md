# WARD security gaps

The [threat model](threat_model.md#accepted-security-limitations) records the accepted limits on
freshness, application authority, manager durability and recovery completeness.

## Access and display

- **Local service / WARDD access.** 
- **On-device disclosure.** Standalone address display can request a label outside the WARD
  application role. On transports without host identity, a queue conflict can display a stored
  value before the user approves revealing it.
  - **Confidentiality in motion.** WARD service requests data from WARDD based on host a request. Therefore, the host can correlate the `entry_key` and identifiers. The confidentiality guarantees are only at rest. 

## Publication and reads

- **Chain evidence.** A public write signature covers the two heads. A manager can accept the
  transition even if `auth_commit` is invalid. Subsequently, devices that need that tag to verify history can then be unable to sync.
  ACCEPTED
- **Queued changes.** A deletion removes the leaf's write counter, and a revert can restore an
  older counter. Both can hide an intervening edit. Interruption between settling a queued change
  and saving the adopted head can also leave the two inconsistent.  -> FIX(redefine deletion)

## Recovery and availability

- **Missing data.** Recovery can reauthorize a head whose encrypted entries the replica can no
  longer reconstruct. A lost response, failed receipt save or incompatible older receipt can
  also leave a previously accepted step unavailable for replay.
- **Recovery date.** After replay, the available receipt may show when the manager last confirmed
  a step rather than when it first accepted it.
- **Late writers.** Until a writer's changes reach Evolu, other hosts cannot serve the manager's
  head. Reads are not current and writes cannot be published. A host cannot tell a late writer from
  a lost one, so only the user can decide to
  [revert to an attested state](ward_roll_forward.md#reverting-to-an-attested-state).
- **Revert and re-application.** Reverting to an attested state and re-applying
  [changes that arrive after a revert](ward_roll_forward.md#changes-that-arrive-after-a-revert)
  are not implemented. The firmware requires the transitions down to the target, and wardd cannot
  publish or rebuild a revert.
- **Replica availability.** Malformed records can block reconstruction. Device reply deadlines
  bound stalled relay exchanges, while a large rebuild can still occupy the service for that wallet.

