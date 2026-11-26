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
