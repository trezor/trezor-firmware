# AuthDB — on-device Merkle Patricia Trie

AuthDB is a Trezor Core firmware app that stores a cryptographic commitment (a Merkle root) to an external database and verifies inclusion/exclusion proofs sent by the host.

## Overview

The device stores:

| Storage key | Type | Description |
|---|---|---|
| `_ROOT` | 32 bytes | Current MPT root hash (`None` when tree is empty) |
| `_COUNTER` | uint32 | Monotonically increasing **root counter**; incremented on every write |

Each leaf also carries its own per-address **leaf counter** (see "Counter" below) --
this is a different, per-address concept from the tree-wide root counter above,
and is committed into the leaf hash itself, not stored as separate device state.

The host maintains the full database and the Merkle tree; the device only stores the root and verifies proofs.

---

## Identity: `device_id` vs `wallet_id`

AuthDB distinguishes two identities, both 32 bytes:

| | `device_id` | `wallet_id` |
|---|---|---|
| Represents | the physical Trezor hardware unit | one mnemonic + passphrase combination (one hidden wallet) |
| Source | `SHA-256(storage.device.get_device_id())` -- reuses the existing random 12-byte device id already exposed via `Features.device_id` | `SLIP21(seed_with_passphrase, [b"AUTHDB WALLET ID"]).key()` |
| Survives seed wipe? | Yes (by design; `storage.device.get_device_id()` is explicitly preserved across `wipe_device`) | No -- tied to the seed |
| Distinguishes passphrases? | No (one per physical unit) | Yes -- each hidden wallet gets its own tree |
| Used for | attributing which physical unit produced an offline-queued operation | keying the on-device Merkle tree (`_ROOTS`/`_QUEUE`/`_SYNC`, all keyed by `wallet_id`) and deriving MAC key material |

`wallet_id` is what every message below scopes its tree/queue/counter
operations to; it appears on every AuthDb response. `device_id` is only used
for MAC-owner matching on the pre-approval paths (`AuthDbSetRoot`/
`AuthDbUpdateLeaf` request fields, historically named `device_id` even
though they compare against `wallet_id` -- kept for wire compatibility)
and for offline-queue attribution once multiple physical devices share one
host database.

`_derive_mac_key()` is scoped to `wallet_id`, not `device_id`: since it is
seed-derived, **the same wallet loaded on two different physical Trezors
produces the identical MAC key**. This is intentional -- it is what makes
root-attestation tokens (see "Fast-forward" below) portable across every
device that has unlocked a given wallet.

---

## Merkle Patricia Trie (MPT)

### Why MPT instead of a sparse Merkle tree (SMT)?

A fixed-depth 256-level SMT produces proofs of exactly 256 × 33 = 8 448 bytes.  This exceeds the 8 704-byte firmware wire buffer when combined with message framing.  The MPT is path-compressed: only branch points where leaves actually diverge are stored.  For N entries the proof has O(log N) elements, each 33 bytes (1-byte bit-position + 32-byte sibling hash).

### Hashing scheme

```
leaf_hash(address, counter, value) = SHA-256(b"\x00" + address + counter(4B BE) + value)
internal_hash(left, right)         = SHA-256(b"\x01" + left + right)   # positional, not sorted
```

`counter` is the address's **leaf counter** (see "Counter" below): a first-class,
cryptographically-committed per-address version number, not just text embedded in the
opaque `value` blob. INIT/INSERT require `counter == 1`; every subsequent UPDATE for
the same address must present `new_counter == old_counter + 1`, enforced on-device by
`compute_new_root()`. DELETE only needs `old_counter` (to reconstruct the leaf being
removed); the counter becomes irrelevant once a leaf is virtual (empty value).

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
node      = SHA-256(b"\x00" + address + counter(4B BE) + value)   # leaf hash
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

Installs an attested root, verified exactly like `AuthDbFastForwardRoot`, and then
replays this wallet's own pending offline queue on top of it in the same call --
`AuthDbSetRoot` is a superset of `AuthDbFastForwardRoot` + `AuthDbApplyOfflineOperations`
in one round trip. `mac` is a **required** field.

```
AuthDbSetRoot {
    required bytes  root       = 1;
    required bytes  mac        = 2;  // required; all-zero accepted only in debug builds
    optional bytes  device_id  = 3;  // must equal wallet_id when mac is non-zero
    optional uint32 counter    = 4;  // target counter; required when mac is non-zero
    repeated AuthDbRebasedOperation operations = 5;  // replayed after install, may be empty
}
AuthDbSetRootResponse {
    required uint32 counter               = 1;
    optional bytes  wallet_id             = 2;
    optional bytes  new_root              = 3;
    required uint32 applied_count         = 4;
    required uint32 last_applied_sequence = 5;
    optional bytes  root_mac              = 6;
}
```

Non-zero `mac` is verified as `HMAC(root_mac_key, wallet_id || counter || root) == mac`,
requiring `device_id == wallet_id` and `counter` strictly greater than the wallet's
current counter (anti-rollback) -- the identical scheme `AuthDbFastForwardRoot` uses.
`mac == b"\x00" * 32` (32-byte all-zero sentinel) is accepted **only in debug builds**
and skips root/counter attestation entirely (installs `root` and bumps the counter by
one); any other unverifying `mac` is rejected before any storage write happens. The
`operations` replay step always runs with full per-op verification (see "Offline
synchronization" below) regardless of which root-install path was taken.

### `AuthDbLookup` (2302) / `AuthDbLookupResponse` (2303)

Verify a membership or non-membership proof.

```
AuthDbLookup {
    required bytes  address         = 1;
    optional bytes  value           = 2;  // required for membership
    repeated bytes  proof           = 3;  // 33 bytes each, leaf-to-root
    optional bytes  witness_address = 4;  // non-membership: witness leaf address
    optional bytes  witness_value   = 5;  // non-membership: witness leaf value
    optional uint32 counter         = 6;  // membership: target leaf's counter
    optional uint32 witness_counter = 7;  // non-membership: witness leaf's counter
}
AuthDbLookupResponse {
    required bool   valid      = 1;
    required uint32 counter    = 2;  // root counter, not the leaf counter above
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
    optional uint32 old_counter     = 9;  // absent/0 on INSERT/INIT
    required uint32 new_counter     = 10; // must be 1 on INSERT/INIT, old_counter+1 on UPDATE
    optional uint32 witness_counter = 11; // INSERT: witness leaf's counter
}
AuthDbUpdateLeafResponse {
    required uint32 counter  = 1;  // root counter
    optional bytes  new_root = 2;  // absent if tree is now empty
}
```

---

## Operations

### Membership proof (`AuthDbLookup`)

```python
tree = AuthDbTree()
leaf_counter = tree.insert(b"alice", b"data_alice")  # 1 (first insert)
root = tree.get_root_hash()
authdb.set_root(session, root)               # debug builds: mac defaults to the zero sentinel

proof = tree.get_proof(b"alice")
valid, membership, counter = authdb.lookup(
    session, address=b"alice", value=b"data_alice", proof=proof, counter=leaf_counter
)
# valid=True, membership=True
```

### Non-membership proof (`AuthDbLookup`)

A non-membership proof proves that an address is **not** in the tree by supplying a *witness* leaf W that occupies the address's path:

1. W is in the tree (membership proof for W passes against stored root).
2. W ≠ target address.
3. W and the target share the same bit-value at every branch in the proof (W truly occupies the target's path).

```python
proof, w_addr, w_counter, w_val = tree.get_nonmembership_proof(b"zara")
valid, membership, counter = authdb.lookup(
    session,
    address=b"zara",
    value=None,
    proof=proof,
    witness_address=w_addr,
    witness_counter=w_counter,
    witness_value=w_val,
)
# valid=True, membership=False
```

**Empty tree**: `get_nonmembership_proof()` returns `([], None, None, None)`.  Pass these directly to `authdb.lookup()`; the firmware checks that no root is stored.

### `AuthDbUpdateLeaf` operations

| Operation | `old_value` | `new_value` | `old_counter` | `new_counter` | `proof` | `witness_*` |
|---|---|---|---|---|---|---|
| INIT (empty tree) | `b""` | non-empty | absent/0 | `1` | `[]` | absent |
| INSERT | `b""` | non-empty | absent/0 | `1` | non-membership proof for address | required |
| UPDATE | non-empty | non-empty | current leaf counter | `old_counter + 1` | membership proof for `(address, old_counter, old_value)` | absent |
| DELETE | non-empty | `b""` | current leaf counter | ignored | membership proof for `(address, old_counter, old_value)` | absent |

`new_counter` is enforced device-side by `compute_new_root()` -- a mismatched claim
(e.g. skipping a counter value, or reusing an already-consumed one) is rejected with
`DataError` before any storage write. This is what makes "the only difference between
two conflicting writes is which counter value they claim" a fact the device itself can
verify, rather than something a host has to trust (see "Conflict resolution" below).

#### INSERT example

```python
# Tree has alice; insert bob
proof, w_addr, w_counter, w_val = tree.get_nonmembership_proof(b"bob")
counter, new_root = authdb.update_leaf(
    session,
    address=b"bob",
    old_value=b"",
    new_value=b"data_bob",
    new_counter=1,
    proof=proof,
    witness_address=w_addr,
    witness_counter=w_counter,
    witness_value=w_val,
)
tree.insert(b"bob", b"data_bob")
assert new_root == tree.get_root_hash()
```

#### UPDATE example

```python
# alice is at counter 1; bump to counter 2 with a new value
proof = tree.get_proof(b"alice")
counter, new_root = authdb.update_leaf(
    session,
    address=b"alice",
    old_value=b"data_alice",
    new_value=b"data_alice_v2",
    old_counter=1,
    new_counter=2,
    proof=proof,
)
tree.insert(b"alice", b"data_alice_v2")  # AuthDbTree.insert() bumps its own counter to match
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
    old_counter=tree.get_counter(b"alice"),
    new_counter=0,  # ignored on DELETE
    proof=proof,
)
tree.delete(b"alice")
assert new_root == tree.get_root_hash()  # or None if tree became empty
```

---

## Security notes

### `AuthDbSetRoot` requires a verified MAC (debug zero-MAC bypass only)

`AuthDbSetRoot` no longer lets the host inject an arbitrary root unauthenticated.
`mac` is a required field, verified with the exact same preimage
`AuthDbFastForwardRoot` uses (`HMAC(root_mac_key, wallet_id || counter || root)`),
including the anti-rollback `counter` check. Only `mac == b"\x00" * 32` bypasses
attestation, and only in debug builds -- production firmware rejects the zero
sentinel and any other unverifying MAC with `DataError` before touching storage.
Use `AuthDbUpdateLeaf` for authenticated production root updates from scratch, or
`AuthDbSetRoot`'s verified path (or `AuthDbFastForwardRoot`) to install a root
another device already attested to.

### `AuthDbUpdateLeaf` is safe for production

The device always **computes** the new root from the supplied proof and the old/new values.  The host never supplies the new root directly.  The device verifies the old state first; if the proof is invalid the operation is rejected without modifying storage.

### Counter

There are two, deliberately distinct, counters:

* **Root counter** (`_COUNTER`, tree-wide): every write operation
  (`AuthDbSetRoot`, `AuthDbUpdateLeaf`, offline-op replay, fast-forward) increments
  this persistent monotonic counter. It says *the tree changed*, not *which address
  changed* -- useful for replay/rollback detection and for `AuthDbFastForwardRoot`'s
  anti-rollback check, but it cannot distinguish "alice changed" from "bob changed."
* **Leaf counter** (per-address, committed into `leaf_hash()` itself): a
  cryptographically-committed version number for one specific address. INIT/INSERT
  require `new_counter == 1`; UPDATE requires `new_counter == old_counter + 1`,
  enforced device-side by `compute_new_root()`. This is what lets the device (not
  just the host) tell "two writes raced to update the same address" apart from "an
  attacker replayed a stale write" -- see "Conflict resolution" below.

Earlier drafts of this doc described the leaf counter as a future, not-yet-implemented
proposal (see [`docs/authdb-sync-proposal.md`](authdb-sync-proposal.md) Part 1) -- it
is now implemented as described above.

### Conflict resolution: counter-only conflicts can auto-merge

Two offline writers racing to update the same address, from the same starting
`old_counter`/`old_value`, produce two operations that both claim
`new_counter == old_counter + 1`. The device accepts whichever one is replayed
first and rejects the other as a sequence/counter conflict -- it never silently
picks a winner. If a host determines the two conflicting writes carry the *same*
intended `new_value` (a pure counter race, not a real content conflict), it is safe
to auto-merge without user approval, since the device still independently verifies
every counter transition. The merge is two ordinary `AuthDbUpdateLeaf` operations
(or two `AuthDbRebasedOperation` entries applied via `AuthDbApplyOfflineOperations`/
`AuthDbSetRoot`), chained back-to-back:

1. **Apply existing**: re-affirm the value that's already canonical on-device as an
   ordinary UPDATE, `old_counter=N, new_counter=N+1` (content-wise a no-op, but it
   establishes a known-consistent counter to chain from).
2. **Apply increase of counter**: a second UPDATE with the same value again,
   `old_counter=N+1, new_counter=N+2` -- so the final leaf counter reflects that
   *two* writes happened, rather than the second writer's attempt silently
   collapsing into nothing.

If the two operations' `new_value`s differ, this is a real content conflict, not a
counter race -- auto-merge does not apply, and the host must fall back to its normal
conflict UI/policy. The decision of *when* the two values are "the same" (and thus
whether to synthesize the two-step batch above) is host/Suite policy; the firmware's
only job is to enforce that whatever counter transition is claimed actually happened
in that exact order.

---

## Offline synchronization

When the host database is unreachable, the device can queue signed operations
locally and apply them later once a host has rebased them against the
current canonical tree.

| Message | Purpose |
|---|---|
| `AuthDbQueueOfflineOperation` (2320) | Create a signed offline operation and append it to the on-device queue. Does not touch the root. |
| `AuthDbGetOfflineOperations` (2322) | Return the current root/counter plus every queued operation, for upload. |
| `AuthDbApplyOfflineOperations` (2324) | Apply a batch of host-rebased operations. |
| `AuthDbDeleteOfflineOperations` (2326) | Garbage-collect applied operations from the queue. |

Design invariants (see `core/src/apps/authdb/apply_offline_operations.py` and
`_mpt.py` for the implementation):

* **The device computes the resulting root itself**, from `(address,
  old_value, new_value, proof)`, exactly as `AuthDbUpdateLeaf` does. A host
  never supplies a root directly, for the same reason `AuthDbSetRoot` is
  debug-only.
* **The MAC binds the exact leaf transition *and* the sequence number**:
  `mac = HMAC(mac_key, sequence || leaf_hash(address, old_counter, old_value) ||
  leaf_hash(address, new_counter, new_value))`. Since `leaf_hash()` is itself
  counter-aware (see "Hashing scheme" above), this binds the leaf counter
  transitively -- no separate MAC-scheme change was needed when the leaf counter
  was introduced. Binding the sequence number prevents a
  host from replaying an approved operation under a different (inflated)
  sequence number, which would otherwise corrupt garbage collection (see
  next point). Binding the leaf values means an approved operation cannot
  later be applied with a different value than what was actually approved.
* **Operations are applied strictly in ascending order**, starting at
  `last_applied_sequence + 1`. Processing stops at the first operation that
  fails its sequence/MAC/proof check, so a conflict can never be silently
  skipped over.
* **Garbage collection takes no host input.** `AuthDbDeleteOfflineOperations`
  only ever deletes up to the device's own persisted `last_applied_sequence`
  -- never a host-supplied watermark -- since deleting an operation that was
  never actually applied would permanently and silently lose it.
* No approval dialog is shown when applying: it already happened when the
  operation was queued, and the MAC cryptographically binds that approval to
  the exact `(sequence, address, old_value, new_value)` being applied.

**Persistence-before-deletion is a host-side invariant the protocol cannot
enforce.** Deletion is safe only when two independent conditions both hold:
(1) the host has durably persisted the write into its own canonical
database, and (2) the device has independently verified and applied it
(reflected in `last_applied_sequence`). `AuthDbApplyOfflineOperations` only
proves (2). Hosts MUST treat "rebased against the canonical tree" as
implying the canonical write already happened -- the canonical tree only
ever reflects committed state -- and MUST NOT call
`AuthDbDeleteOfflineOperations` until they have separately confirmed their
own database write is durable (e.g. past fsync/replication), even though the
RPC does not require or check this.

## Fast-forward: `AuthDbFastForwardRoot` (2328) / `Response` (2329)

Lets a wallet's root be advanced directly to a state some device has already
attested to, skipping replay of every individual operation in between.
**Safe for production firmware** -- unlike `AuthDbSetRoot`, the host cannot
mint an arbitrary `(root, mac)` pair; it can only replay a root-attestation
token a device already produced:

* `AuthDbUpdateLeafResponse.mac` and `AuthDbApplyOfflineOperationsResponse.root_mac`
  are both `HMAC(mac_key, wallet_id || counter || new_root)` -- a
  root-attestation token, computed whenever any device updates the tree.
* Because `mac_key` is wallet-scoped (seed-derived), **a token issued by one
  physical device is valid on every other physical device that has unlocked
  the same wallet**. This is what makes fast-forward useful for the
  three-devices-one-database scenario: any device that already advanced the
  tree can hand another device a shortcut to the same state.
* The device verifies `msg.wallet_id` matches its own current `wallet_id`,
  recomputes `mac_key`, and checks `mac` against `wallet_id || counter ||
  new_root` from inside the request -- **never a bare, separately-supplied
  counter field**. This closes a specific replay hole: without binding the
  counter into the MAC, a host could pair a genuinely-issued old
  `(root, mac)` with a forged, higher counter and bypass the monotonicity
  check below.
* The device rejects unless `msg.counter` is strictly greater than its own
  currently-stored counter for this `wallet_id` (anti-rollback).

**`AuthDbSetRoot` answers the open question above for its own call**: rather than
leaving "what happens to my locally-queued ops after a fast-forward" unspecified,
`AuthDbSetRoot`'s `operations` field installs the attested root *and* replays the
device's own pending queue on top of it, atomically, in one round trip -- see
`AuthDbSetRoot` above. Calling bare `AuthDbFastForwardRoot` directly (with no
replay) still leaves that question open for that specific call, unchanged.

[`docs/authdb-sync-proposal.md`](authdb-sync-proposal.md) records the per-leaf counter
(Part 1, now implemented -- see "Counter" above) and a Suite-side conflict-history
design (recording every applied op per address, attributed by `device_id`, so a host
can display "what happened on all Trezors since the last canonical root"), and
separately proposes how the same primitives extend to fully offline Bluetooth
peer-to-peer sync between two Trezors (Part 2, not implemented).

## CLI

**Note:** the CLI below has not yet been updated for the mandatory-`mac`/leaf-counter
wire changes described in this document -- `set-root`, `lookup`, `update-leaf`, and
the offline-sync commands need new counter/mac arguments before they will work
against current firmware. Tracked as follow-up work; use `python/src/trezorlib/authdb.py`'s
wrapper functions directly in the meantime.

```
trezorctl authdb set-root <root_hex>          # debug only

trezorctl authdb lookup <addr_hex> <val_hex> -p <sib> ...
trezorctl authdb lookup <addr_hex> -p <sib> ... \
    --witness-address <w_addr_hex> --witness-value <w_val_hex>

trezorctl authdb update-leaf <addr_hex> <old_hex> <new_hex> [-p <sib> ...]
trezorctl authdb update-leaf <addr_hex> "" <new_hex> -p <sib> ... \
    --witness-address <w_addr_hex> --witness-value <w_val_hex>

trezorctl authdb delete <addr_hex> <old_hex> [-p <sib> ...]

trezorctl authdb approve <addr_hex> <old_hex> <new_hex>

# Offline synchronization
trezorctl authdb queue-offline-operation <addr_hex> <old_hex> <new_hex>
trezorctl authdb get-offline-operations
trezorctl authdb apply-offline-operations --file rebased_ops.json
trezorctl authdb delete-offline-operations

# Fast-forward (skip replay, jump to an already-attested state)
trezorctl authdb fast-forward-root <new_root_hex> <counter> <wallet_id_hex> <mac_hex>
```

Note: offline-cache commands (`set-cache-entry`/`get-cache-entry`/
`get-all-cache`/`wipe-cache`) are a separate, unrelated feature -- an
on-device label cache, not part of the sync protocol above.

---

## Host library

```python
from trezorlib.authdb_tree import AuthDbTree, EMPTY_ROOT
from trezorlib import authdb

tree = AuthDbTree()
counter = tree.insert(b"alice", b"data_alice")  # counter == 1

# Membership
proof = tree.get_proof(b"alice")
assert AuthDbTree.verify_proof(b"alice", counter, b"data_alice", proof, tree.get_root_hash())

# Non-membership
nm_proof, w_addr, w_counter, w_val = tree.get_nonmembership_proof(b"unknown")
assert AuthDbTree.verify_nonmembership(b"unknown", nm_proof, w_addr, w_counter, w_val, tree.get_root_hash())

# Update (bumps the leaf counter by exactly 1)
counter = tree.insert(b"alice", b"data_alice_v2")  # counter == 2

# Delete
tree.delete(b"alice")    # or tree.insert(b"alice", b"")
```

---

## File index

| File | Description |
|---|---|
| `common/protob/messages-authdb.proto` | Protobuf message definitions |
| `common/protob/messages.proto` | Wire-type IDs (2300–2329) |
| `core/src/storage/authdb.py` | Persistent storage: `_ROOTS`/`_CACHE`/`_QUEUE` (next sequence is derived, not separately persisted) |
| `core/src/storage/device.py` | Physical `device_id` primitive (reused, not AuthDB-specific) |
| `core/src/apps/authdb/__init__.py` | `device_id`/`wallet_id`/MAC-key derivation |
| `core/src/apps/authdb/_mpt.py` | Shared MPT hash/proof primitives |
| `core/src/apps/authdb/set_root.py` | `AuthDbSetRoot` handler (debug only) |
| `core/src/apps/authdb/lookup.py` | `AuthDbLookup` handler |
| `core/src/apps/authdb/update_leaf.py` | `AuthDbUpdateLeaf` handler |
| `core/src/apps/authdb/approve.py` | `AuthDbApprove` handler |
| `core/src/apps/authdb/clear_root.py` | `AuthDbClearRoot` handler (debug only) |
| `core/src/apps/authdb/queue_offline_operation.py` | `AuthDbQueueOfflineOperation` handler |
| `core/src/apps/authdb/get_offline_operations.py` | `AuthDbGetOfflineOperations` handler |
| `core/src/apps/authdb/apply_offline_operations.py` | `AuthDbApplyOfflineOperations` handler (thin wrapper around `_replay.py`) |
| `core/src/apps/authdb/_replay.py` | Shared offline-op replay loop, used by both `apply_offline_operations.py` and `set_root.py` |
| `core/src/apps/authdb/delete_offline_operations.py` | `AuthDbDeleteOfflineOperations` handler |
| `core/src/apps/authdb/fast_forward_root.py` | `AuthDbFastForwardRoot` handler |
| `docs/authdb-sync-proposal.md` | Leaf counter (Part 1, implemented) + conflict-history design spec + Bluetooth peer-sync extension (Part 2, not implemented) |
| `core/src/apps/workflow_handlers.py` | Message → handler routing |
| `python/src/trezorlib/authdb_tree.py` | Host-side MPT (insert, delete, proofs) |
| `python/src/trezorlib/authdb.py` | Host-side RPC wrappers + `sync_offline_queue()` |
| `python/src/trezorlib/cli/authdb.py` | `trezorctl authdb` CLI commands |
| `core/tests/test_apps.authdb.py` | Unit tests (proof verification, storage, `_mpt`) |
| `tests/device_tests/misc/test_authdb.py` | Device integration tests |
