# The authenticated tree

The host stores encrypted entries in a tree. The Trezor retains a root that commits to every keyed
path and its encrypted content. The same encrypted entries produce the same root in any insertion
order. Adding and then deleting an entry can therefore restore an earlier root at a later counter.

| Operation | What the Trezor verifies |
| --- | --- |
| Read | The ciphertext at the requested path belongs to the trusted root. |
| Prove absence | The tree is empty, or a verified different entry occupies the route the requested path would take. |
| Write or delete | Evidence of the old entry or its absence lets the device derive the new root. A host rebuilding the tree can reproduce it independently. |

An entry deleted from the current tree can survive in encrypted replica history. The root identifies
the contents. [Transitions and sessions](ward_transitions.md) establish how the wallet reached them.

## Recovery after data loss in Evolu

Suppose the WARD Manager accepted change N, but the writing host went offline before Evolu
replicated it. A second host can rebuild only through an older change M, so M < N. The manager
still holds the root for N. Its attestation identifies the tree the replica needs to serve, but
contains none of the missing entries. The replica reports that it is behind. Proofs against root M
cannot establish what is stored at root N, and new writes must build on N, so the wallet can
neither read current values nor publish until the replica catches up.

Evolu cannot tell a late copy from a lost one. Each transition travels as one record that carries
both the step and its encrypted entries, so the step from M to N is missing exactly as long as its
entries are.

- **If the changes are late,** the host rebuilds from them once they arrive. It checks the root at
  each step. Once it reproduces the manager's head at N, it can serve proofs there again.
- **If the user decides not to wait,** they can accept the contents at M as of the time the
  manager attested M. The revert restores those contents under a new counter. See
  [reverting to an attested state](ward_roll_forward.md#reverting-to-an-attested-state).
- **If the changes arrive after that revert,** they are not lost. They sit on a dead branch and
  can be re-added. See
  [changes that arrive after a revert](ward_roll_forward.md#changes-that-arrive-after-a-revert).

The seed recovers the wallet keys. Individual values may also survive as
[pinned copies or queued changes](user_story.md#keeping-a-contact-while-offline).
