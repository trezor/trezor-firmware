# F4 Merkle trie

The Trezor stores no entry values in the tree, only one 32-byte root per wallet next to the
counter. wardd keeps the tree, hashes without keys and serves proofs. The device uses proofs to
accept presence, accept absence and derive the next root for its own change; it never takes a root
from a host ([the authenticated tree](../ward-trie.md)).

- The root depends only on the set of `(entry_key, value_digest)` pairs, not on insertion order.
- Every trusted root was derived by a device from the empty tree, so it is canonical.
- A proof gives authenticity and position, never freshness
  ([what a verified read means](../threat_model.md#what-a-verified-read-means)).

## F4.1 Implement canonical leaf and branch hashing

A path-compressed binary trie over 256-bit `entry_key`s, most significant bit first
([leaf](../ward_leaf_encryption.md#leaf)):

| Node | Hash |
| --- | --- |
| Value digest | `SHA-256(0x03 ‖ sealed_content)` |
| Leaf | `SHA-256(0x00 ‖ entry_key ‖ value_digest)`, both exactly 32 bytes |
| Branch | `SHA-256(0x01 ‖ split_bit ‖ left ‖ right)`, split bit in one byte |
| Empty tree | `SHA-256(0x02)` |

Children are positional; a one-entry root is its leaf hash; every branch splits at the first bit
where its keys diverge. A branch hashes its split bit, not its depth, so moved subtrees keep their
hash and relabelling changes every hash above. Wrong-width operands abort as malformed.

## F4.2 Implement membership proof verification

The proof is a leaf-to-root list of (one-byte split bit, 32-byte sibling). Check the sealed part's
scheme and length; check that split bits strictly increase from the root down and stay below 256
(capping the proof at 256 elements); hash the leaf from the device's own `entry_key`; fold by the
key's bit at each split; compare with the trusted root; only then decrypt.

Reads prove against the stored head or a session-only
[caught-up](../ward_manager.md#catching-up-a-second-trezor) position; writes against the stored
head; a pointer's target against the same root ([lookup](../ward_leaf_encryption.md#lookup)). A
missing root at a non-zero counter means "cannot verify". A failure keeps no state and also covers
a host with missing data ([data loss in Evolu](../ward-trie.md#recovery-after-data-loss-in-evolu)).

## F4.3 Implement non-membership proof verification

Proven absence, a stored empty value and an unavailable entry are distinct results. The host
supplies a witness key, its `value_digest` and its membership proof. Accept absence only if all
three are 32 bytes, the witness key differs from the target, the proof is well formed, the target's
bit equals the witness's at every split bit, and the witness folds to the trusted root. An empty
tree needs no witness; a non-empty tree without one is refused.

Fixed widths prevent a boundary shift (a "witness" of target key plus one digest byte would hash to
the target's own leaf). Soundness rests on canonical roots, which one route cannot check.

## F4.4 Implement insert and update root calculation

Starting from the F4.2/F4.3 read against the stored head:

- **Update:** fold the new leaf along the same proof.
- **Insert:** derive the splice bit (first differing bit of new and witness key), fold the witness
  elements below it into one subtree, join it with the new leaf there, fold the rest.
- **First insert:** the leaf hash, only if the trusted root is the empty constant.

`C_leaf` is the counter of the writing transition. The device authorizes (M, old root) to
(N, new root) without moving its head; adoption comes on a later sync
([from approval to adoption](../ward_transitions.md#from-approval-to-adoption)). In a batch each
entry proves against the previous edit's root. A failed proof aborts before the screen; a lost race
uses the [retry token](../ward_transitions.md#competing-writers).

## F4.5 Implement deletion

Prove the leaf, then remove it: an empty proof yields the empty constant (never "no root");
otherwise the lowest sibling replaces the collapsed parent unchanged and the rest folds up.
Deleting an absent entry is a no-op with no authorization. Deletion needs a live session. Pointers
and targets are deleted independently. Earlier roots still contain the entry.

## F4.6 Restore verified leaves into the offline queue

Move a proven value into the offline store as a pinned copy or a pending change, so no unproven
byte reaches flash. Derive `entry_key` from the identity (or check an opened `sealed_identity`
derives it), verify and open the leaf (a pointer resolves against the same root), check capacity,
then show identity, value, record kind, root freshness and any replaced record (a hold to replace a
different value), and write one record holding only the value. A pending restore is a new intent
published above the current head, never a revert
([re-adding changes](../ward_roll_forward.md#changes-that-arrive-after-a-revert)).

## F4.8 Listing of all or filtered entries

The key holder (the device, or a host with a
[released key](f3-confidential-entries.md#f33-release-application-keys-on-demand-post-mvp)) walks every
leaf, opens content, opens and checks the identity, skips other applications and shows pointers
unfollowed ([listing and restore](../ward_leaf_encryption.md#listing-and-restore)). For a complete
listing the device streams leaves in key order and rebuilds the root with a per-bit stack; strictly
increasing keys and a matching root mark it complete, anything else incomplete. Missing identities
show as unnamed, failing ones as invalid. The device shows a listing only on its screen unless the
user confirms an export.

## Open questions

- **Deletion** discards the last `C_leaf`, hiding intervening edits from conflict detection
  ([security gaps](../gaps.md#publication-and-reads)). Should it leave a tombstone, which would also
  permit a queued offline delete?
- **Restore from earlier roots** needs [F5](f5-chain-history.md) to tie the root to history. What
  base, provenance (counter, attestation time) and multi-entry confirmation should such restores
  carry?
