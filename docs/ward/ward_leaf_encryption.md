# Entry privacy

Devices with the same seed and passphrase derive the same paths and encryption keys. Each wallet
uses distinct keys for paths, identities and contents, shared across its application namespaces.

| Part | Purpose |
| --- | --- |
| Path | A keyed digest of the application namespace, identifier and device scope. It lets the wardd serve an entry while preserving privacy of the identity (only at rest). |
| Content | The encrypted entry type, last write counter and value. The tree commits to this ciphertext at the path. |
| Identity | The namespace, identifier and scope, encrypted separately beside the tree. Lookup by a known identifier works without this record. |

Each AES-256-GCM encryption uses always a fresh random nonce. 

## Reading a label

The Trezor derives the path from the address and its namespace. The host returns the encrypted
entry and a proof against the selected root. The device verifies the proof before decrypting and
displaying the label. If the entry is missing, the host must prove absence. A proven empty label
and a missing entry produce different results on screen.

## Pointers

A pointer names an entry in the same namespace. The Trezor follows the hops and verifies both
lookups against the same root. A missing target yields absence. Once maximum number of pointers is reached or a target
is outside the namespace, the lookup fails. Deleting the pointer leaves its target intact. Deleting the target leaves its pointer intact, and the user is notified on next lookup.
