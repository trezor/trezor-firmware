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

If an Evolu replica loses data, the host can rebuild the tree from encrypted change history
retained by another replica or in a backup. It checks the root after each change. Once it reaches
the wallet's trusted head, the host can again serve proofs for that state.

A partial backup may reproduce only an older head. With a WARD Manager, reverting to that state
requires enough surviving history to verify the target and the user's approval of the
[revert](ward_roll_forward.md#reverting-and-rejoining).

The wallet seed and the manager's signed head cannot recreate a value lost from every replica and
backup. A Trezor may still hold individual [pinned copies or queued changes](user_story.md#keeping-a-contact-while-offline).
