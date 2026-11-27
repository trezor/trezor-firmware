# F2 Authenticated entries

The application names an entry by its `leaf_identity`; the host sees only its `entry_key`, which
the Trezor derives under `K_path`. The trie leaf holds `sealed_content`; `sealed_identity` is
stored beside it ([entry privacy](../ward_leaf_encryption.md)).

- The device always derives `entry_key` itself; a host never picks the path of a read or write.
- Every returned part is verifiably this wallet's and at the right path, or refused.
- Authentication gives no freshness; that comes from proofs against an attested root
  ([F4](f4-merkle-trie.md), [F5](f5-chain-history.md)).

## F2.1 Implement record identities and derive entry keys

Derive the global SLIP-21 keys `K_path`, `K_ident`, `K_data` from the seed (with passphrase); they
stay distinct capabilities ([keys](../ward_leaf_encryption.md#keys)). Per-application
`K_data(app)` is envisioned; `K_path` stays global. Then:

```
leaf_identity = len8(device_id) || device_id || len8(app_id) || app_id
                || len16(identifier) || identifier
entry_key     = HMAC-SHA256(K_path, "WARD PATH v1" || leaf_identity)
```

An empty `device_id` means an entry shared by all devices
([device ID](../ward_leaf_encryption.md#device-id)). `app_id` is assigned by the WARD service, never
chosen by the caller. `entry_type` lives in `leaf_content`, so one identity has one leaf. Missing
or oversized fields are refused before anything is derived. An `entry_key` is stable, so a host
can link lookups ([what each party learns](../threat_model.md#what-each-party-learns)).

## F2.2 Implement identity and content authentication

Seal each part with AES-256-GCM ([sealing](../ward_leaf_encryption.md#sealing)):
`0x01 || nonce(12) || tag(16) || ct`, random nonce per seal, AAD `domain || entry_key`;
`sealed_content` under `K_data` with domain 0x05, `sealed_identity` under `K_ident` with 0x04.

- The nonce is never derived from the leaf: a rollback or second device can rewrite the same
  `(entry_key, C_leaf)`.
- `entry_key` in the AAD stops a part moving to another leaf where no proof is checked
  (re-adding, listing, restore).
- A tag shows only that a key holder sealed the part; content sealed with a
  [released key](f3-confidential-entries.md#f33-release-application-keys-on-demand-post-mvp) is still
  refused because only the device produces trusted roots.
- `C_leaf` (counter of the writing transition) drives
  [conflict detection](../ward_transitions.md#competing-writers).

Check scheme byte and length before hashing or opening. Open `sealed_content` only after its proof
verifies ([lookup](../ward_leaf_encryption.md#lookup)); for listing, check that the opened identity
derives `entry_key` ([listing and restore](../ward_leaf_encryption.md#listing-and-restore)). Any
malformed part or tag failure refuses the whole operation and is never reported as absence.

## F2.3 Add authenticated record messages and test vectors

Define the exchanges, identical on the [wallet and service channels](../ward-channels.md):

- **Read:** device sends `entry_key`; host returns `sealed_content` and proof, or a witness key,
  digest and proof for absence. In a batch, proofs are against the root after prior staged edits.
- **Write:** device returns `entry_key`, both sealed parts (empty for a deletion), the new
  counter, the wallet authentication tag, the public signature for the manager and a retry token.
  A no-op returns no authorization.
- **Storage:** hosts keep sealed parts verbatim, compute digests and serve proofs without keys;
  each transition is replicated with its sealed parts
  ([data loss in Evolu](../ward-trie.md#recovery-after-data-loss-in-evolu)). The manager never sees
  a sealed part.

Use fixed-width big-endian integers, explicit-width length prefixes and a strict reader. The device
never accepts an `entry_key`, root or splice point from a host and refuses a reply of the wrong
shape. One shared fixture set (keys, `entry_key`s, layouts, fixed-nonce seals, leaf hashes, a trie
with proofs, negative cases) is consumed by every implementation.

