# Entry privacy

Devices with the same seed and passphrase derive the same paths and keys, so every Trezor of the
wallet can find and open its entries.

| Part | Purpose |
| --- | --- |
| Path | A keyed digest of the identity. wardd serves the entry without learning the identity. |
| Content | The sealed entry type, write counter and value. The trie commits to it at the path. |
| Identity | The device, application and identifier, sealed beside the trie. A lookup does not need it. |

A WARD leaf sits at a keyed path, `entry_key`, and holds only `sealed_content`. The identity that
derived `entry_key` is encrypted as `sealed_identity`, and it is stored only in the database. Both
are sealed with AES-256-GCM.

## Keys

It is envisioned that each application can have its own data key. However, we should start with a
single global key set only.

```
global:          K_x         = SLIP21(seed, ["ward", "K_x"])
per application: K_data(app) = SLIP21(seed, ["ward", "app", app_id, "K_data"])

for K_x in K_path, K_ident, K_data
```

A "single global key" means one global set of the three keys. They stay distinct, so each remains
a separate capability.

The `app_id` is the domain the WARD service assigns to the caller. It is part of `leaf_identity`,
so applications get separate paths even under the global key set.

| Key | Lets its holder |
| --- | --- |
| `K_path` | Compute the `entry_key` of an identifier it knows |
| `K_data` | Read `leaf_content` |
| `K_ident` | Read `leaf_identity` |

With per-application keys, `WARDExportKeys` releases one application's key after the user confirms
that application on the device.

## Device ID

`device_id` is empty for an entry shared by all devices. Otherwise it is the ID of the device the
entry belongs to, as the firmware assigns it.

## Leaf

```
leaf (in the trie)
├── entry_key           32 B, the trie path in the clear
└── sealed_content      leaf_content sealed under K_data(app), domain 0x02
      entry_type        how to read the value: address, pointer, ...
      C_leaf            counter of the transition that wrote the entry
      value             the entry; for a pointer, the target's leaf_identity

stored beside the leaf
└── sealed_identity     leaf_identity sealed under K_ident(app), domain 0x03
      device_id         empty, or the ID of the device the entry belongs to
      app_id            the caller's domain
      identifier        how the application looks up the entry (an xpub or an address)
```

```
leaf_identity = len8(device_id) || device_id || len8(app_id) || app_id
                || len16(identifier) || identifier
leaf_content  = len8(entry_type) || entry_type || C_leaf:u32 || value
entry_key     = HMAC-SHA256(K_path, "WARD PATH v1" || leaf_identity)
value_digest  = SHA256(0x03 || sealed_content)
leaf_hash     = SHA256(0x00 || entry_key || value_digest)
```

- **`leaf_identity`:** it is not in the trie, because `entry_key` already authenticates it. It is
  kept only for listing and restore.
- **`entry_type`:** it marks an entry as a pointer (symlink) or a plain value. The WARD service
  follows a pointer automatically during a lookup, so the caller receives the target's value.
- **`value_digest`:** it covers sealed bytes only, so a host can compute it and serve proofs for
  leaves it cannot open.
- **`leaf_hash`:** both operands are exactly 32 bytes. Otherwise a host could pass a membership
  proof off as a non-membership proof.

## Sealing

Each part is sealed independently with AES-256-GCM, under its own key and domain:

```
seal(K, domain, pt) = 0x01 || nonce || tag || ct
                      with nonce = 12 random bytes, fresh for every seal
                           aad   = domain || entry_key

sealed_content  = seal(K_data(app),  0x02, leaf_content)
sealed_identity = seal(K_ident(app), 0x03, leaf_identity)
```

- **Random nonce:** the nonce is never derived from the leaf, because a rollback or a second device
  can write the same `(entry_key, C_leaf)` again.
- **AAD:** `entry_key` binds each sealed part to its path, so a part moved to another leaf fails
  its tag. The trie binds content to its path only where a proof is checked. Re-adding, listing
  with a released key and restoring an export can handle a part outside such a proof, and the tag
  then still refuses a part taken from another entry. For `sealed_identity`, the tag also lets a
  holder of `K_ident(app)` alone check that an identity belongs to its path. The domain byte is
  redundant while `K_data` and `K_ident` are different keys.
- **Scheme byte:** the first byte is the scheme. `0x01`, AES-256-GCM, is the only one.

## Reading

### Lookup

1. Derive `entry_key` and get a proof against the authenticated root.
2. Open `sealed_content` with `K_data(app)`. A tag failure is an error.
3. If `entry_type` is `pointer`, the WARD service derives the target's `entry_key` from the
   `leaf_identity` in the value and looks it up against the same root, without the caller asking.
    - The target's `app_id` must be the caller's.
    - A longer chain or a cycle fails the lookup.
    - A target proven absent is "not found".

A lookup never needs `sealed_identity`.

### Listing and restore

The key holder walks every leaf of the verified trie, taking each leaf's `entry_key` from its path:

1. Open `sealed_content` with `K_data(app)`. The trie commits to the sealed content, so this step
   decides whose leaf it is.
    - Under the global key set, a tag failure is an error.
    - Under per-application keys, a tag failure means another application's leaf: skip it.
2. Listing: request and open `sealed_identity` stored beside the leaf with `K_ident(app)`. Verify
   that `HMAC(leaf_identity) = entry_key`.
3. Skip the leaf if its `app_id` is not the caller's.
4. A pointer is shown as a pointer and not followed.

### Re-adding after a revert

Changes that reach the replica after a revert sit on a dead branch from M to N, and the user can
[re-add](ward_roll_forward.md#changes-that-arrive-after-a-revert) them. A content tag shows only
that a holder of `K_data(app)` sealed the value. Re-adding also needs the wallet authentication
tags of the dead branch's transitions, which chain its roots back to the fork point M:

- **Origin:** they prove a late value was written by the wallet on top of M, even if an
  application's data key has been released.
- **Position:** they place each value on the branch, so a host cannot offer an older value of an
  entry that changed again before N. The `entry_key` in the AAD already stops a value of one entry
  from being shown as another's; it cannot tell an older value of the same entry from the latest.
- **Completeness:** they let the Trezor check that the branch accounts for all N − M changes.
- **Revival:** a rejoin or a roll-forward after a manager restore can land on the branch again.

These tags are kept until the branch is [closed](ward_roll_forward.md#closing-a-dead-branch). The
revert's own tag is on the current history and is always kept: every later walk must tell the
revert from a commit.
