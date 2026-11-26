# WARD trie conformance

The canonical tree uses SHA-256. Each domain prefix below is one byte. Each path, digest, root and child hash is exactly 32 bytes. A branch bit is one unsigned byte, numbered from the most significant bit of the path.

| Digest | Input in order |
| --- | --- |
| Value | 03 (hex), sealed content |
| Leaf | 00 (hex), keyed path, value digest |
| Branch | 01 (hex), branch bit, left child hash, right child hash |
| Empty tree | 02 (hex) |

A branch splits on the first differing bit of the paths below it, with zero on the left. A single leaf stands alone. Branch digests are independent of depth. Insertion creates the first differing branch and deletion promotes the surviving sibling unchanged.

A proof lists the branch bit and sibling hash for each level from leaf to root. Read from root to leaf, branch bits must strictly increase. For an absence proof in a nonempty tree, the witness path must differ from the requested path, belong to the tree, and agree with the requested path at every branch in the proof. An empty root directly proves absence.

The conformance vectors record the root after each change so incremental updates can be compared with an independent rebuild. See [the authenticated tree](../../../../docs/ward/ward-trie.md) for the role of these proofs in a wallet.
