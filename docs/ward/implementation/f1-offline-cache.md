# F1 Offline cache in miniscript

The offline cache works with no host service, no replicated store and no manager. The Trezor keeps
a small set of records per passphrase wallet in its PIN-protected storage. In the miniscript
release they hold wallet policy approvals; later they also hold pinned copies of proven values and
the queue of local changes WARD publishes from
([keeping a contact while offline](../user_story.md#keeping-a-contact-while-offline)).

- Records never leave the device except through a confirmed plaintext export
  ([backing up local work](../user_story.md#backing-up-local-work)).
- Every record is scoped to one passphrase wallet by a secret identifier derived from the seed.
- Every write, replacement or removal is confirmed on the device. The store never evicts.
- Each record is one storage item, so an interrupted write leaves the old or the new record.

## F1.1 Implement persistent offline record storage

Reserve a pool of storage slots for WARD records, separate from heads, pairings and settings and
shared by all passphrase wallets. A record is named by a 16-byte wallet identifier (SLIP-21 from
the seed, never exported), a record type, a namespace and an identifier; the name may be stored in
full or as a digest keyed by the wallet identifier, so it cannot be listed without the secret. The
value follows with a flags byte (queued or pinned) and, for a queued change, its base: the stored
head's counter when it was queued.

Use one canonical encoder and a header that stays fixed across format versions, so an unparseable
newer record can still be found and erased. Lookups match version, wallet and full name. A read
returns valid, missing or unreadable, never missing for an unreadable record.

## F1.2 Implement offline add, update, delete and lookup

- **Queue a change:** check size, record the base, show the new value beside any value it
  replaces, and say it is held, not applied. A second change to the entry replaces the first.
- **Pin a copy:** only in a synced session, store a value read by a proven lookup (a pointer as
  its resolved value). Needs the [authenticated tree](../ward-trie.md), so not in miniscript.
- **Discard a queued change** or **erase a local copy** (including an unreadable one): held
  confirmation showing what is lost. Discarding never touches a pinned copy.
- **Look up:** on-device features read without confirmation and learn the value's source
  ([showing an address label](../user_story.md#showing-an-address-label)). The feature picks the
  source (proven read when synced, else local record) before asking, so a host cannot steer it.

Host requests can name only label records; the namespace separates but grants nothing. Only the
host with the WARD application role may ask on the paired Trezor Host Protocol; on older
transports the device asks before revealing a stored value
([wallet channel](../ward-channels.md#wallet-channel)). A local erase is not a WARD deletion and
vice versa. Queueing over an unreadable record is refused until the user erases it.

## F1.3 Add listing and storage capacity handling

A value may hold up to 1 KiB (a BIP-388 policy fits) and a record has its own cap. The pool has a
slot count and a byte budget. All limits are checked before any confirmation screen; a full pool
answers "erase an entry first", and a replacement pays only the size difference.

Add a host-facing listing of the active wallet's records: type, namespace, identifier, state and
value size (never the value), plus the count of unreadable records and the room left. It follows
the same host checks as a read. Digest-named records do not appear. The room left is pool-wide.

## F1.4 Implement authenticated queue backup export

After a confirmation that shows the value and says it leaves the device, export one named record in
plaintext. A queued change carries an HMAC-SHA256 tag under a SLIP-21 wallet authentication key
over a domain label, the wallet's public WARD identifier, the operation and the length-prefixed
type, namespace, identifier and value, encoded independently of storage. A pinned copy has no tag.
The tag proves only that this wallet once queued these bytes: no counter, no base, no freshness.
Plaintext is the accepted exception in [what each party learns](../threat_model.md#what-each-party-learns).
An unreadable record fails the export.

## F1.5 Implement backup validation and restore

Verify the tag in constant time before any screen, so no field can be altered or moved to another
name or passphrase wallet. Check capacity, then show what the restore replaces and that the change
comes from a backup and is not applied. A restored change is queued with no base; at publication
any different published value is a [conflict](../user_story.md#keeping-a-contact-while-offline)
for the user, and an equal value settles it without a write. Only the confirmation and the conflict
check limit replay.

## F1.6 Connect policy registration and offline reuse

On registration the device validates the policy, shows template, keys and name, and stores an
approval: a queued record of a policy type only this feature writes, named by a digest of the
canonical template-and-keys encoding, holding that encoding and the name. Re-registering identical
bytes is a silent no-op; a duplicate name is refused.

When an operation presents a policy, an exact byte match with the approval skips the registration
screen (the operation's own confirmations remain); anything else leads back to registration. No
host proof or network is needed. A host cannot create an approval; a restore brings one back only
with this wallet's tag over the policy type and a confirmation showing the policy. Removal needs a
held confirmation. [F8](f8-migration.md) can later publish approvals to WARD.

## Open questions

- Should restore be bounded against replay, so an old valid backup cannot bring back an outdated
  pending change? [Security gaps](../gaps.md#publication-and-reads) should record the answer.

## Related

- [User stories](../user_story.md) and [participants and channels](../ward-channels.md)
