# AuthDB — on-device Merkle Patricia Trie

AuthDB is a Trezor Core firmware app that stores a cryptographic commitment (a Merkle root) to an external database and verifies inclusion/exclusion proofs sent by the host.

## Overview

The device stores:

| Storage key | Type | Description |
|---|---|---|
| `_ROOT` | 32 bytes | Current MPT root hash (`None` when tree is empty) |
| `_COUNTER` | uint32 | Monotonically increasing counter; incremented on every write |

The host maintains the full database and the Merkle tree; the device only stores the root and verifies proofs.

---

## Merkle Patricia Trie (MPT)

### Why MPT instead of a sparse Merkle tree (SMT)?

A fixed-depth 256-level SMT produces proofs of exactly 256 × 33 = 8 448 bytes.  This exceeds the 8 704-byte firmware wire buffer when combined with message framing.  The MPT is path-compressed: only branch points where leaves actually diverge are stored.  For N entries the proof has O(log N) elements, each 33 bytes (1-byte bit-position + 32-byte sibling hash).

### Hashing scheme

```
leaf_hash(address, value)  = SHA-256(b"\x00" + address + value)
internal_hash(left, right) = SHA-256(b"\x01" + left + right)   # positional, not sorted
```

The `b"\x00"` / `b"\x01"` domain-separation prefixes prevent second-preimage attacks.

### Path encoding

The path through the tree for an address is the bit sequence of `SHA-256(address)`, MSB first (bit 0 = most significant bit of byte 0).  Only the bits at actual branch points appear in the proof.

### Proof format

Each proof element is **33 bytes**:
- byte 0: bit-position in the SHA-256(address) path (0–255)
- bytes 1–32: 32-byte sibling hash

Elements are ordered **leaf-to-root**.

### Verification (membership)

```
addr_hash = SHA-256(address)
node      = SHA-256(b"\x00" + address + value)   # leaf hash
for (bit, sibling) in proof:                      # leaf-to-root
    if addr_hash[bit] == 0:
        node = SHA-256(b"\x01" + node + sibling)
    else:
        node = SHA-256(b"\x01" + sibling + node)
return node == stored_root
```

### Empty tree

An empty tree has no root.  `get_root_hash()` returns `EMPTY_ROOT` (32 zero bytes) to signal this; the firmware stores `None`.

---

## Value format

The `value` field is an opaque byte string.  For the AuthDB use-case the recommended encoding is:

```
<domain>:<counter>:<lifecycle>:<metadata_json>
```

| Component | Description |
|---|---|
| `domain` | Application domain (e.g. `ethereum`, `bitcoin`) |
| `counter` | Version counter for optimistic concurrency |
| `lifecycle` | `ACTIVE`, `ARCHIVED`, or `REVOKED` |
| `metadata_json` | JSON object with additional fields |

**Delete semantics**: deleting an entry means setting its value to empty bytes.  An entry with an empty value is a *virtual node*: it is excluded from the MPT leaf set.  This is identical in effect to never having inserted it.  This simplifies non-membership proofs because "not in tree" and "deleted" are the same state.

---

## Wire messages

All messages are defined in `common/protob/messages-authdb.proto`.

### `AuthDbSetRoot` (2300) / `AuthDbSetRootResponse` (2301)

**Debug builds only.**  Injects an arbitrary root into persistent storage.  Rejected on production firmware.  Use `AuthDbUpdateLeaf` for production root updates.

```
AuthDbSetRoot        { required bytes root = 1 }
AuthDbSetRootResponse{ required uint32 counter = 1 }
```

### `AuthDbLookup` (2302) / `AuthDbLookupResponse` (2303)

Verify a membership or non-membership proof.

```
AuthDbLookup {
    required bytes address         = 1;
    optional bytes value           = 2;  // required for membership
    repeated bytes proof           = 3;  // 33 bytes each, leaf-to-root
    optional bytes witness_address = 4;  // non-membership: witness leaf address
    optional bytes witness_value   = 5;  // non-membership: witness leaf value
}
AuthDbLookupResponse {
    required bool   valid      = 1;
    required uint32 counter    = 2;
    optional bool   membership = 3;  // true = membership, false = non-membership
}
```

### `AuthDbUpdateLeaf` (2304) / `AuthDbUpdateLeafResponse` (2305)

Atomically verify old state and update a leaf.  The device computes the new root; the host never supplies it.  Safe for production firmware.

```
AuthDbUpdateLeaf {
    required bytes  address         = 1;
    required bytes  old_value       = 2;  // empty = address absent
    required bytes  new_value       = 3;  // empty = delete
    repeated bytes  proof           = 4;  // 33 bytes each, leaf-to-root
    optional bytes  witness_address = 5;  // INSERT: non-membership witness
    optional bytes  witness_value   = 6;  // INSERT: non-membership witness
}
AuthDbUpdateLeafResponse {
    required uint32 counter  = 1;
    optional bytes  new_root = 2;  // absent if tree is now empty
}
```

---

## Operations

### Membership proof (`AuthDbLookup`)

```python
tree = AuthDbTree()
tree.insert(b"alice", b"data_alice")
root = tree.get_root_hash()
authdb.set_root(session, root)               # debug builds

proof = tree.get_proof(b"alice")
valid, membership, counter = authdb.lookup(
    session, address=b"alice", value=b"data_alice", proof=proof
)
# valid=True, membership=True
```

### Non-membership proof (`AuthDbLookup`)

A non-membership proof proves that an address is **not** in the tree by supplying a *witness* leaf W that occupies the address's path:

1. W is in the tree (membership proof for W passes against stored root).
2. W ≠ target address.
3. W and the target share the same bit-value at every branch in the proof (W truly occupies the target's path).

```python
proof, w_addr, w_val = tree.get_nonmembership_proof(b"zara")
valid, membership, counter = authdb.lookup(
    session,
    address=b"zara",
    value=None,
    proof=proof,
    witness_address=w_addr,
    witness_value=w_val,
)
# valid=True, membership=False
```

**Empty tree**: `get_nonmembership_proof()` returns `([], None, None)`.  Pass these directly to `authdb.lookup()`; the firmware checks that no root is stored.

### `AuthDbUpdateLeaf` operations

| Operation | `old_value` | `new_value` | `proof` | `witness_*` |
|---|---|---|---|---|
| INIT (empty tree) | `b""` | non-empty | `[]` | absent |
| INSERT | `b""` | non-empty | non-membership proof for address | required |
| UPDATE | non-empty | non-empty | membership proof for `(address, old_value)` | absent |
| DELETE | non-empty | `b""` | membership proof for `(address, old_value)` | absent |

#### INSERT example

```python
# Tree has alice; insert bob
proof, w_addr, w_val = tree.get_nonmembership_proof(b"bob")
counter, new_root = authdb.update_leaf(
    session,
    address=b"bob",
    old_value=b"",
    new_value=b"data_bob",
    proof=proof,
    witness_address=w_addr,
    witness_value=w_val,
)
tree.insert(b"bob", b"data_bob")
assert new_root == tree.get_root_hash()
```

#### DELETE example

```python
proof = tree.get_proof(b"alice")
counter, new_root = authdb.update_leaf(
    session,
    address=b"alice",
    old_value=b"data_alice",
    new_value=b"",
    proof=proof,
)
tree.delete(b"alice")
assert new_root == tree.get_root_hash()  # or None if tree became empty
```

---

## Security notes

### `AuthDbSetRoot` is debug-only

`AuthDbSetRoot` lets the host inject an arbitrary root.  On production firmware the root must be derived from actual leaf insertions via `AuthDbUpdateLeaf`.  Accepting an external root would allow an attacker to forge the entire database state.  The firmware rejects this message with `DataError` on non-debug builds.

### `AuthDbUpdateLeaf` is safe for production

The device always **computes** the new root from the supplied proof and the old/new values.  The host never supplies the new root directly.  The device verifies the old state first; if the proof is invalid the operation is rejected without modifying storage.

### Counter

Every write operation (set_root, update_leaf) increments a persistent monotonic counter.  Callers can use the counter to detect replay attacks or concurrent modifications.

---

## CLI

```
trezorctl authdb set-root <root_hex>          # debug only

trezorctl authdb lookup <addr_hex> <val_hex> -p <sib> ...
trezorctl authdb lookup <addr_hex> -p <sib> ... \
    --witness-address <w_addr_hex> --witness-value <w_val_hex>

trezorctl authdb update-leaf <addr_hex> <old_hex> <new_hex> [-p <sib> ...]
trezorctl authdb update-leaf <addr_hex> "" <new_hex> -p <sib> ... \
    --witness-address <w_addr_hex> --witness-value <w_val_hex>

trezorctl authdb delete <addr_hex> <old_hex> [-p <sib> ...]
```

---

## Host library

```python
from trezorlib.authdb_tree import AuthDbTree, EMPTY_ROOT
from trezorlib import authdb

tree = AuthDbTree()
tree.insert(b"alice", b"data_alice")

# Membership
proof = tree.get_proof(b"alice")
assert AuthDbTree.verify_proof(b"alice", b"data_alice", proof, tree.get_root_hash())

# Non-membership
nm_proof, w_addr, w_val = tree.get_nonmembership_proof(b"unknown")
assert AuthDbTree.verify_nonmembership(b"unknown", nm_proof, w_addr, w_val, tree.get_root_hash())

# Delete
tree.delete(b"alice")    # or tree.insert(b"alice", b"")
```

---

## File index

| File | Description |
|---|---|
| `common/protob/messages-authdb.proto` | Protobuf message definitions |
| `common/protob/messages.proto` | Wire-type IDs (2300–2305) |
| `core/src/storage/authdb.py` | Persistent storage: root + counter |
| `core/src/apps/authdb/set_root.py` | `AuthDbSetRoot` handler (debug only) |
| `core/src/apps/authdb/lookup.py` | `AuthDbLookup` handler + proof verifier |
| `core/src/apps/authdb/update_leaf.py` | `AuthDbUpdateLeaf` handler |
| `core/src/apps/workflow_handlers.py` | Message → handler routing |
| `python/src/trezorlib/authdb_tree.py` | Host-side MPT (insert, delete, proofs) |
| `python/src/trezorlib/authdb.py` | Host-side RPC wrappers |
| `python/src/trezorlib/cli/authdb.py` | `trezorctl authdb` CLI commands |
| `core/tests/test_apps.authdb.py` | Unit tests (proof verification) |
| `tests/device_tests/misc/test_authdb.py` | Device integration tests |
