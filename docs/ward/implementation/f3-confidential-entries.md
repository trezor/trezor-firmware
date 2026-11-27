# F3 Confidential entries

Hosts store WARD tree data they cannot read or forge. The Trezor derives every key from the seed
and passphrase, so devices of one wallet agree without exchange and hidden wallets share nothing
([entry privacy](../ward_leaf_encryption.md)).

- Keys are derived on demand and never stored.
- Nothing is decrypted before its proof verifies, and failed authentication never yields plaintext.
- Confidentiality is at rest only: a relaying host can correlate identifiers with `entry_key`s
  ([access and display](../gaps.md#access-and-display)), and exports are plaintext by design.

## F3.1 Derive offline cache encryption keys

```
K_x         = SLIP21(seed, ["ward", "K_x"])          for K_x in K_path, K_ident, K_data
K_data(app) = SLIP21(seed, ["ward", "app", app_id, "K_data"])          envisioned
```

`K_path` and `K_ident` never leave the device and stay global: `app_id` already separates paths,
and the identity names the application, so its key cannot depend on `app_id`
([keys](../ward_leaf_encryption.md#keys)). `K_data` never leaves under the global key set. A released application key reveals
nothing about its parent or siblings. Separately derive the change-authorizing keys: the wallet
authentication key (transitions, queued intents, retry tokens) and the Ed25519 key whose public key
identifies the wallet to the manager; only that public key is exported. Never reuse a label.

## F3.2 Encrypt and decrypt offline cache entries

Implement the tree seal ([sealing](../ward_leaf_encryption.md#sealing)):
`0x01 || nonce(12) || tag(16) || ct`, AES-256-GCM, random nonce per seal, AAD
`domain || entry_key`, domain 0x05 for content under `K_data` and 0x04 for identity under
`K_ident`. A repeated nonce would leak plaintext XOR and the GCM subkey; random nonces keep a
wallet far below the collision bound.

Offline cache records are not sealed by WARD: device storage already encrypts them under the PIN,
and they leave only via confirmed plaintext export with the queued intent's wallet tag
([F1.4](f1-offline-cache.md#f14-implement-authenticated-queue-backup-export)). A malformed or
modified part aborts before any screen; an unreadable record is reported.

## F3.3 Release application keys on demand (post-MVP)

Under per-application keys, release `K_data(app)` for the caller's `app_id` only, after a held
screen that names the application and says the release is permanent (revoking means re-keying).
Under the global key set, refuse. On the paired protocol only the host with the
[WARD application role](../ward-channels.md#wallet-channel) may ask. Never release `K_path`, a
global key, another application's key or a change-authorizing key. Release is stateless.

The holder reads its values by walking the verified trie, skipping leaves its key cannot open
([listing and restore](../ward_leaf_encryption.md#listing-and-restore)). `K_ident` is never
released, so names are listed through the device. Content it seals itself is
still refused by devices.
