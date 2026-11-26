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

Suppose the WARD Manager accepted head N, but the writing host went offline before Evolu
replicated its last changes. A second host can rebuild only through M, where M < N. The manager
still attests N. Its signed root identifies the state the host needs to serve, but cannot recover
the missing entries. This host reports that its replica is behind. It cannot use M to prove a
current value or publish a new write from M.

Each replicated record carries a transition and its encrypted changes together. The second host
cannot tell whether a missing record is delayed or permanently lost. If the writer reconnects, or
a surviving replica or backup supplies the records, the host traces the chain back from N and
replays it forward, checking each resulting root. Current reads and writes can resume on this host
when its rebuilt head matches the manager's current counter and root.

If no copy of a required record survives, the current recovery flow stops. The Trezor needs the
intervening history to authorize a revert, and the local service cannot yet publish or rebuild one.
The proposed [revert to an attested state](ward_roll_forward.md#reverting-to-an-attested-state)
would let the user approve the contents at M under a new counter, N + 1. If the missing changes
later arrive, the proposal allows the user to [re-add them individually](ward_roll_forward.md#changes-that-arrive-after-a-revert).

The seed recovers the wallet keys. Individual values may also survive as
[pinned copies or queued changes](user_story.md#keeping-a-contact-while-offline).
