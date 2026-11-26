# Entry privacy

Devices with the same seed and passphrase derive the same paths and encryption keys. Each wallet
uses distinct keys for paths, identities and contents, shared across its application namespaces.

| Part | Purpose |
| --- | --- |
| Path | A keyed digest of the application namespace, identifier and device scope. It lets the replica serve an entry without knowing its name. |
| Content | The encrypted entry type, last write counter and value. The tree commits to this ciphertext at the path. |
| Identity | The namespace, identifier and scope, encrypted separately beside the tree. Lookup by a known identifier works without this record. A recovered identity must reproduce the path. |

Each AES-256-GCM encryption uses a fresh random nonce, including on retries. Ordinary writes are wallet-wide.
Per-device assignment, per-application key delegation, bulk key export, verified listing and
automatic identity repair remain proposals. The [threat model](threat_model.md#what-each-party-learns)
describes what observers can learn from a lookup.

## Pointers

A pointer names an entry in the same namespace. The Trezor follows one hop and verifies both
lookups against the same root. A missing target yields absence. A second pointer or a target
outside the namespace fails the lookup. Deleting the pointer leaves its target intact.
