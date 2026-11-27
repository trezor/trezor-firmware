# F8 Migration from the miniscript store

The miniscript release keeps policy approvals and other records only in each Trezor's offline
store, per passphrase wallet and application. Migration replicates them through the wallet's tree
so they survive device loss and reach the wallet's other devices: once the user enables
replication, the device checks each destination against its trusted root, publishes the sealed
value, and keeps the record locally with a sticky mark.

Migration adds no new path into the tree: each record becomes an ordinary queued change, published
like any other ([F7](f7-rollback-batching.md)), with or without a WARD Manager.

Invariants:

- The upgrade rewrites nothing; the new firmware reads the old record format, and derives the
  wallet identifier, wallet authentication key and public WARD identifier exactly as before
  (fixed by shared test vectors), so records are found and old backups verify.
- Nothing is published until the user enables replication for that wallet on the device.
- Records are never deleted by migration; they stay usable as local approvals throughout.

## Starting state

Each record is a queued change of its wallet, never offered, with base counter zero (the wallet had
no head); a record restored from backup has no base. Migration needs a stored head: a wallet
without one first catches up from the empty tree. If no head slot is free, migration stops with
that reason and the wallet stays offline-only.

## Enabling replication

A per-wallet setting confirmed on the device, which shows how many records will be published and
that their values will be stored encrypted on the user's hosts. Hosts holding the replicated
records then learn that entries exist, their sizes and history, but not their contents
([what each party learns](../threat_model.md#what-each-party-learns)). Wallets that are not
unlocked are untouched.

## Mapping and publishing records

Each record keeps namespace, identifier and subscope; its type becomes the sealed entry type. The
device derives the entry path with the wallet's path key, so a host cannot redirect a record
([entry privacy](../ward_leaf_encryption.md)). Only queued records of a known type are eligible;
unreadable ones are reported, never deleted; compact records are published only when the host
names them.

For each record the device obtains a membership or absence proof against its trusted root
([the authenticated tree](../ward-trie.md)). A withheld or stale proof leaves the record queued.

| Destination | Outcome |
| --- | --- |
| Absent | Publish the record. |
| Same type and value | Settle without a write. |
| Different value | Show both; the user keeps the published value, publishes the local one, or defers. |

With base zero, any difference is a [conflict](../user_story.md#keeping-a-contact-while-offline).
Two devices that approved the same policy converge: one publishes, the other finds the same value
and settles.

Publication is the normal path: seal identity and content, derive the new root, authorize M → N,
optionally batching up to eight records all-or-nothing, with claims filed before release
([from approval to adoption](../ward_transitions.md#from-approval-to-adoption)). A record settles
only when its own transition is verified on adoption.

## Marking migrated records

When an adopted head settles a migrated record, by publication, a matching value or the user
keeping the published value, the record becomes a pinned copy and gets a sticky migration mark in
its flags. Offline reuse of an approval keeps working because it reads queued and pinned records
alike. The mark says the value also lives in the replicated store; the device uses it to report
when a wallet's migration is complete and must preserve it across every later flag rewrite. A new
change queued over the record replaces it with an ordinary queued change, which needs no mark.

## Backups made before migration

Old backups stay valid (same keys). A restored record arrives queued with no base and migrates like
any other; the restore screen and conflict check put discarded or superseded values before the user
([backing up local work](../user_story.md#backing-up-local-work)).

## Interruption and power loss

Apart from the replication setting, migration keeps no progress state: each record is queued,
offered or migrated, so it can stop and resume anywhere. Offers, lost replies and full stores
behave as for any queued change ([F7.1](f7-rollback-batching.md#f71-implement-persistent-pending-edit-management));
the settle-then-save window is the gap in [publication and reads](../gaps.md#publication-and-reads).

## Open questions

- The proposal names the sticky flag in one line. Is "set when the record settles" the intended
  meaning, and is the mark needed beyond reporting completion?

## Related

- [Keeping a contact while offline](../user_story.md#keeping-a-contact-while-offline)
- [Publication and reads gaps](../gaps.md#publication-and-reads)
