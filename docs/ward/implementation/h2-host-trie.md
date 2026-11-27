# H2 Host trie reconstruction

**Depends on:** [F4 Merkle trie](f4-merkle-trie.md) and
[H1 wardd and host adapter](h1-wardd-host-adapter.md).

The Trezor keeps only a root per wallet and verifies every proof against it
([the authenticated tree](../ward-trie.md)). wardd keeps the whole tree, rebuilds it from
replicated transition records and serves proofs, without any [keys](../ward_leaf_encryption.md#keys).
A host error can only make entries unavailable, so the host's job is to build exactly the root
devices derived. Hashes are keyless: leaf H(0x00 ‖ entry key ‖ value digest), branch
H(0x01 ‖ split bit ‖ left ‖ right), empty tree H(0x02), value digest H(0x03 ‖ sealed content).
Hosts store sealed parts verbatim and rebuild from append-only records, checking every
intermediate root ([H3](h3-history-reconstruction.md)).

## H2.1 Build the canonical host trie from records

Build the tree at a chosen head from the wallet's records. A record names its starting and
resulting states, the wallet tag, its kind (commit or revert), any kept manager signature, and its
changes (path with sealed content and sealed identity, or a deletion). Follow
[F4.1](f4-merkle-trie.md#f41-implement-canonical-leaf-and-branch-hashing): the root depends only on
the set of (path, value digest) pairs; operands are exactly 32 bytes; two leaves at one path are
refused; the empty tree is the fixed constant and a missing root is never read as empty. Sealed
identities are kept for [listing and restore](../ward_leaf_encryption.md#listing-and-restore) and
never hashed. A cached tree is checked against a from-scratch rebuild.

The host cannot check wallet tags; the device judges. It checks that each record reproduces its
root, that kept manager records verify, and in the manager-free build that the publication
signature verifies under the wallet's public identifier, for replicated records as well as its own.
Appending never replaces a stored record. A record that fails these checks or cannot be parsed is
skipped and counted, never aborting the load.

## H2.2 Generate membership and non-membership proofs

Serve evidence for [F4.2](f4-merkle-trie.md#f42-implement-membership-proof-verification) and
[F4.3](f4-merkle-trie.md#f43-implement-non-membership-proof-verification): for a present path, the
sealed content and a leaf-to-root proof; for an absent path, the leaf on the target's route with its
value digest and proof, never its ciphertext (none for an empty tree). Never serve the sealed
identity on a read.

Serve at the manager's head (manager-free: the highest buildable head). On the service channel the
device names its head, and a host at another head asks it to sync. A host that cannot build the
required head answers "behind" instead of serving older proofs. All pulls of one device call, such
as a pointer [lookup](../ward_leaf_encryption.md#lookup), use one pinned head. Within a batch
([F7.2](f7-rollback-batching.md#f72-prepare-and-validate-batch-transitions)), serve from a scratch
copy with the staged changes applied, so each proof matches the device's running root. Listing
([F4.8](f4-merkle-trie.md#f48-listing-of-all-or-filtered-entries)) needs a path-ordered stream of
leaves with proofs.

## H2.3 Apply stored insert, update and delete transitions

Apply the device's write results and replicated records
([F4.4](f4-merkle-trie.md#f44-implement-insert-and-update-root-calculation),
[F4.5](f4-merkle-trie.md#f45-implement-deletion)). A write result holds up to eight changes (empty
sealed content deletes), the new counter, the wallet tag and the publication signature. The host
checks it was made on its current head, applies it, and verifies the publication signature over its
head and the computed root, catching any root disagreement before storing. It then appends one
record and submits the step to the manager.

A commit advances the counter by its number of changes; a revert by exactly one
([counter rules](../ward_transitions.md#why-commits-count-changes-and-reverts-count-one)). A revert
from N to target M carries no changes: the tree at N + 1 copies the tree at M, so the tree at N is
never needed. A revert ends the device's write session; wardd publishes it and syncs again.

A lost race leaves a record no head walks through; keep it for rejoin. A failed append fails the
request. A manager conflict goes to the [retry path](../ward_transitions.md#competing-writers). A
crash between append and submission leaves a headless record; the device stays at M and offers its
queued change again.

## H2.4 Match host roots and proofs against firmware

Build one corpus of seeded operation sequences (insert, update, delete, batches of up to eight) over
several key geometries (random, long shared prefixes, a ladder), with the root and served proofs
after each step. One generator writes it; the firmware repository holds it; other repositories copy
it and check its hash. Firmware, the Rust trie and every host replay it, and none keeps its own
vectors. A device run drives the emulator through wardd: the adopted root must equal the host's
rebuilt root, and the device must accept or refuse each proof as expected, including tampered ones
(relabelled split bit, witness off the route).

## Related

- [Entry privacy](../ward_leaf_encryption.md)
- [From approval to adoption](../ward_transitions.md#from-approval-to-adoption)
- [Recovery and availability](../gaps.md#recovery-and-availability)
