# WARD leaf encryption

A WARD leaf sits at a keyed path, `entry_key`, and holds only `sealed_content`. The identity which derived `entry_key` is encrypted as `sealed_identity`, and it is stored only in database. Both are sealed with AES-256-GCM.

## Keys

It is envisioned that each application can have its own data key. However, we should start with a single global key set only.

```
global:          K_x = SLIP21(seed, ["ward", "K_x"])   for K_x in K_path, K_ident, K_data
per application: K_data(app) = SLIP21(seed, ["ward", "app", app_id, "K_data"])
```

A "single global key" means one global set of the three keys. They stay distinct, so each remains a separate capability. Under the global key set, `K_x(app)` below is the global `K_x`.

The seed includes the passphrase, so every hidden wallet has its own key set.

The `app_id` is the domain the WARD service assigns to the caller. It is part of `leaf_identity`, so applications get separate paths even under the global key set.

| Key | Lets its holder |
| --- | --- |
| `K_path` | Compute the `entry_key` of an identifier it knows |
| `K_data` | Read `leaf_content` |
| `K_ident` | Read `leaf_identity` |

`WARDExportKeys` releases keys only after the user confirms on the device:

- Under the global key set, it releases `K_path`, `K_data` and `K_ident`.
- With per-application keys, it releases one application's key after the user confirms that application.

`K_sig` is never exported. The host keeps exported keys in memory only.

## Device ID

`device_id` is empty for an entry shared by all devices. Otherwise it is a single byte, 1 to 255: the slot of the device the entry belongs to, as the firmware assigns it.

## Leaf

```
leaf (in the trie)
├── entry_key           32 B, the trie path in the clear
└── sealed_content      leaf_content sealed under K_data(app), domain 0x02
      entry_type        how to read the value: address, pointer, ...
      C_leaf            counter of the transition that wrote the entry
      value             the entry; for a pointer, the target's leaf_identity

stored beside the leaf
└── sealed_identity     leaf_identity sealed under K_ident(app), domain 0x04
      device_id         empty, or the slot of the device the entry belongs to
      app_id            the caller's domain
      identifier        what the application looks the entry up by (xpub, address)
```

```
leaf_identity = len8(device_id) || device_id || len8(app_id) || app_id
                || len16(identifier) || identifier
leaf_content  = len8(entry_type) || entry_type || C_leaf:u32 || value
entry_key     = HMAC-SHA256(K_path(app), "WARD PATH v1" || leaf_identity)
value_digest  = SHA256(0x03 || sealed_content)
leaf_hash     = SHA256(0x00 || entry_key || value_digest)
```

| Field | Bound |
| --- | --- |
| `device_id` | Empty, or 1 byte |
| `app_id` | At most 255 bytes |
| `entry_type` | At most 255 bytes |
| `identifier` | At most 65,535 bytes |
| `value` | Runs to the end of `leaf_content`; no bound of its own |

- **`leaf_identity`:** it is not in the trie, because `entry_key` already authenticates it. It is kept only for listing.
- **`entry_type`:** it marks an entry as a pointer (symlink) or a plain value. The WARD service follows a pointer automatically during a lookup, so the caller receives the target's value.
- **`C_leaf`:** every leaf of one transition carries that transition's counter. The device reads it with the value, and the offline cache stores it with each cached entry.
- **`value_digest`:** it covers sealed bytes only, so a host can compute it and serve proofs for leaves it cannot open. `0x03` is the trie's value domain; it is a hash prefix, not a sealing domain.
- **`leaf_hash`:** both operands are exactly 32 bytes. Otherwise a host could pass a membership proof off as a non-membership proof.
- **Delete:** a transition deletes an entry with an empty `sealed_content` at its `entry_key`, which removes the leaf from the trie. A delete has no `leaf_content` and no `sealed_identity`.

## Sealing

Each part is sealed independently with AES-256-GCM, under its own key and domain:

```
seal(K, domain, pt) = 0x01 || nonce || tag || ct
                      with nonce = 12 random bytes, fresh for every seal
                           tag   = 16 bytes
                           aad   = domain

sealed_content  = seal(K_data(app),  0x02, leaf_content)
sealed_identity = seal(K_ident(app), 0x04, leaf_identity)
```

- **Random nonce:** the nonce is never derived from the leaf, because a rollback or a second device can write the same `(entry_key, C_leaf)` again.
- **AAD:** The sealing is separated by domain, but as long as `K_data` and `K_ident` are different keys, this separation is redundant. The identity domain is `0x04` so that no sealing domain equals the trie's value domain `0x03`.
- **Scheme byte:** the first byte is the scheme. `0x01`, AES-256-GCM, is the only one.
- **Length:** a sealed part is at least 29 bytes: scheme, nonce and tag.

## Reading

### Lookup

1. Derive `entry_key` and get a proof against the authenticated root.
2. Open `sealed_content` with `K_data(app)`. A tag failure is an error.
3. If `entry_type` is `pointer`, the WARD service derives the target's
   `entry_key` from the `leaf_identity` in the value and looks it up against
   the same root, without the caller asking.
    - The target's `app_id` must be the caller's.
    - A longer chain or a cycle fails the lookup.
    - A target proven absent is "not found".

A pointer is written with `WardSetPointer`, which names the target identifier in
the caller's own `app_id`; the target need not exist yet. Overwriting or deleting
a pointer shows what it pointed to; deleting it leaves the target untouched.

A lookup never needs `sealed_identity`. It knows the identity, though, so it
returns a freshly sealed one, which the host uses to repair a missing or bad
identity row.

**Privacy limit:** `K_path` keeps parties that only store the trie (Evolu, the
WARD Manager) from mapping identifiers to paths. It does not hold against the
host connected to an unlocked device: a lookup shows no screen, so that host can
have the device compute the `entry_key` of any identifier it can guess. Values
stay sealed under `K_data` either way.

### Listing

Not implemented on this branch. This is the specified behavior.

The key holder walks every leaf of the verified trie, taking each leaf's
`entry_key` from its path:

1. Open `sealed_content` with `K_data(app)`. The trie commits to the sealed
   content, so this step decides whose leaf it is.
    - Under the global key set, a tag failure is an error.
    - Under per-application keys, a tag failure means another application's
      leaf: skip it.
2. Open the `sealed_identity` candidates stored beside the leaf, at most 4,
   newest first, with `K_ident(app)`. Use the first one for which
   `HMAC(leaf_identity) = entry_key`. If none passes, show the entry as unknown
   and report its `entry_key` to the host for repair; never skip it.
3. Skip the leaf if its `app_id` is not the caller's.
4. A pointer is shown as a pointer and not followed:
    - The screen shows the pointer's own identifier, an arrow, and the target's
      identifier, taken from the `leaf_identity` in the pointer's value.
    - The listing does not look the target up, so it shows no target value and
      does not prove the target exists. An existing target appears as its own
      entry.
    - A pointer whose target `app_id` is not the caller's is shown as invalid,
      because a lookup would refuse to follow it.
