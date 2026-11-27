# S1 Suite backup UX

**Depends on:** [F3](f3-confidential-entries.md) (and
[F3.2](f3-confidential-entries.md#f32-encrypt-and-decrypt-offline-cache-entries) for S1.2).

S1 is the Suite side of the offline cache ([F1](f1-offline-cache.md)), usable before any local
store or manager exists: registering wallet policies the Trezor approves, and
[backing up local work](../user_story.md#backing-up-local-work). The device decides whether a
policy is approved and whether a backup is genuine; Suite explains, collects intent and moves bytes
between device and file, and its statuses are hints. Policies, identifiers, values and backups
never reach analytics, crash reports, logs or any remote endpoint.

## S1.1 Build Suite policy registration and offline views

Register a policy after Suite checks that it parses, fits the value limit and has an unused name;
the device validates, shows and stores the approval
([F1.6](f1-offline-cache.md#f16-connect-policy-registration-and-offline-reuse)). Outcomes:
registered, already registered, name taken, store full, declined. The offline view matches the
wallet's policies to the device listing
([F1.3](f1-offline-cache.md#f13-add-listing-and-storage-capacity-handling)) by approval digest and
shows free room; anything not read this session is "not checked". Approvals live on one Trezor
until restored (S1.2) or [migrated](f8-migration.md). Suite never edits approvals; removal needs a
hold on the device, which never evicts.

## S1.2 Build Suite backup and restore actions

Export selected queued changes and approvals: the device shows each value and says it leaves the
device ([F1.4](f1-offline-cache.md#f14-implement-authenticated-queue-backup-export)). The file is
plaintext with wallet authentication; Suite says so, keeps no copy and uploads nothing. Pinned
copies are not exported.

Restore sends one record at a time; the device checks authentication before any screen, names what
it replaces and says the change is not applied
([F1.5](f1-offline-cache.md#f15-implement-backup-validation-and-restore)). A restored change has no
base counter, so a differing published value later asks the user
([keeping a contact while offline](../user_story.md#keeping-a-contact-while-offline)). Suite warns
that a backup can revive a discarded or published change
([F7.6](f7-rollback-batching.md#f76-protect-recovery-against-authorization-replay)), and rereads the
listing after an interruption.

## Open questions

- Matching approvals needs policy records in the listing and shared digest vectors.
- Where Suite keeps the policies themselves.

## Related

- [What each party learns](../threat_model.md#what-each-party-learns) and
  [access and display gaps](../gaps.md#access-and-display)
