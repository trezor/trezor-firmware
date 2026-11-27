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
  older counter. Both can hide an intervening edit.  -> FIX(redefine deletion)
- **Settle, then save.** Adopting a head N from a stored head M is two separate storage writes,
  and a power cut can fall between them.
  1. **Settle.** Every queued change the device handed to a host has a claim. The device decides
     for each claim whether its transition landed: it is among the transitions the walk from M to
     N verified, or, for a single change, its authorization re-derives from M to N. A landed change
     becomes a plain cached copy and stops being queued. A change that did not land is offered
     again. The claim is then deleted.
  2. **Save.** The device stores N as its head.

  The order is deliberate: the single-change check reads M, the head being replaced. Within
  settlement each claim's flags are written before the claim is deleted, so a cut never loses an
  unsettled claim, and the next adoption settles the rest.

  A cut after settling and before saving leaves the stored head at M while the landed changes are
  no longer queued:
  - **Usually harmless.** The next sync adopts N, or a head above it, again and the two agree.
  - **Silent loss.** If the current history drops N before that, the change survives only as a
    cached copy. This happens after a revert approved on another device, a restored manager that
    is not rolled forward, or a rejoin onto another branch. Offline reads still show the value,
    labeled as not checked, but nothing offers it again and no screen says it was dropped.
  - **Wrong base.** A newer queued change of the same entry had its base moved to the landed
    change's counter. Its conflict check at the next flush then refers to a state the device never
    adopted.

  A change judged not landed is offered again. Its old authorization was bound to an ended session,
  so it cannot land as well. Saving first is no better: the landed changes would stay queued and be
  offered again. A flush would settle them without publishing while the value is still current,
  but would ask the user if another writer changed the entry since.

  Possible fixes: record the adoption target before settling and finish an interrupted adoption on
  the next sync; make settlement and the head one storage transaction; or store the from-state in
  each claim, so settlement no longer needs M and can follow the save.

## Recovery and availability

- **Missing data.** Recovery can reauthorize a head whose encrypted entries wardd can no
  longer reconstruct. A lost response, failed receipt save or incompatible older receipt can
  also leave a previously accepted step unavailable for replay.
- **Recovery date.** After replay, the available receipt may show when the manager last confirmed
  a step rather than when it first accepted it.
- **Late writers.** Until a writer's changes reach Evolu, other hosts cannot serve the manager's
  head. Reads are not current and writes cannot be published. A host cannot tell a late writer from
  a lost one, so only the user can decide to
  [revert to an attested state](ward_roll_forward.md#reverting-to-an-attested-state).
- **After a revert.** Reviewing [late changes](ward_roll_forward.md#changes-that-arrive-after-a-revert)
  and [closing a discarded branch](ward_roll_forward.md#closing-a-dead-branch) remain proposals.
- **Local data availability.** Malformed records can block reconstruction. Device reply deadlines
  bound stalled relay exchanges, while a large rebuild can still occupy the service for that wallet.

