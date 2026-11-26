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

Suppose the WARD Manager accepted change 24, but the writing host went offline before Evolu
replicated it. A second host can rebuild only through change 23. The manager still holds the
root for 24. Its attestation identifies the tree the replica needs to serve, but contains none
of the missing entries. The replica reports that it is behind. Proofs against root 23 cannot
establish what is stored at root 24.

- **If the writing host, another replica or a backup still has the missing changes,** the host
  can rebuild from that history. It checks the root at each step. Once it reproduces the
  manager's head at 24, it can serve proofs there again.
- **If the only copy was lost before synchronization,** waiting for Evolu cannot recover it.
  Returning to the contents at 23 requires a [verified revert](ward_roll_forward.md#reverting-and-rejoining).
  The Trezor must have enough surviving transition evidence to verify the target, and the user
  must approve. The revert restores those contents under a new counter. Without that evidence,
  the older backup alone cannot restore service at the manager's head.

The seed recovers the wallet keys. Individual values may also survive as
[pinned copies or queued changes](user_story.md#keeping-a-contact-while-offline).
