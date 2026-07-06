# AuthDB synchronization: counter-in-leaf-and-root proposal

**Status: Part 1 is implemented and shipped.** The leaf-counter design below (breaking change to
the leaf-hash preimage, `new_counter == old_counter + 1` enforcement, and the wire/handler changes
in the table at the end of Part 1) has landed in firmware, storage, and the wire protocol exactly
as described — `docs/authdb.md` now documents it as shipped. **Part 2 (Bluetooth peer-to-peer
sync) and Part 3 (cross-device conflict history) remain proposal/design-only, not implemented.**
Part 3 in particular is a **Suite-side design spec**: firmware exposes everything it needs
(attribution via `Features.device_id`, per-op old/new value and counter via
`AuthDbGetOfflineOperations`), but the actual history log can only be held by Suite, since only
Suite ever observes every device's queue contents before replaying them — implementing it requires
work in the Suite repository, out of this repo's scope. Follow-on implementation work for Parts 2
and 3 should be planned separately once their open questions are resolved, in the same spirit as
the evaluation that preceded Part 1's implementation.

## Current state and prerequisite bugs

AuthDB already implements the full mechanical pipeline for Suite-mediated sync: a per-wallet
root+counter record (`core/src/storage/authdb.py` `_ROOTS`), a wallet-scoped offline operation
queue (`_QUEUE`/`_SYNC`), and production-safe handlers to drain the queue
(`AuthDbGetOfflineOperations`), replay it against a freshly-rebased proof
(`AuthDbApplyOfflineOperations`), and skip a device ahead to a state another device already
attested to (`AuthDbFastForwardRoot`). The device remains the sole authority for root computation
throughout — a host can only replay attestations a device itself produced, since MACs are
wallet-derived (seed+passphrase), not device-derived, and are therefore portable across every
physical Trezor holding the same wallet.

Two bugs were found while reviewing this pipeline, and have since been fixed (both were
prerequisites for testing the design below end-to-end):

- `_derive_mac_key()` (`core/src/apps/authdb/__init__.py:47`) is declared with **zero parameters**,
  but every call site — `update_leaf.py:28-29`, `set_root.py:31`, `fast_forward_root.py:42`,
  `queue_offline_operation.py:39`, `approve.py:23`, `apply_offline_operations.py:26-27` — invokes it
  as `_derive_mac_key(b"root_mac")` or `_derive_mac_key(b"leaf_approval")`. As written this raises
  `TypeError` at every call. Even a fix that accepts-and-ignores the argument would silently
  collapse the two "different" MAC keys into one, defeating the evident intent of domain-separated
  keys.
- `set_root.py`'s MAC preimage (`HMAC(root_mac_key, root)`, debug-only) is inconsistent with the
  `wallet_id || counter || root` shape used everywhere else (`update_leaf.py`,
  `fast_forward_root.py`, `apply_offline_operations.py`). A token minted by one cannot be verified
  by the other.

Today's counter lives **only in the root record** (`storage/authdb.py:16`, `_RECORD_SIZE=68`:
`[root:32][wallet_id:32][counter:4]`) — one monotonic `uint32` per wallet, bumped on every
mutating op. It answers "has the tree changed," not "which address changed, and relative to what."
The `value` field's recommended `<domain>:<counter>:<lifecycle>:<metadata_json>` encoding
(`docs/authdb.md` "Value format") is an **unenforced application convention**: the device never
parses or checks it.

---

## Part 1 — counter-in-leaf-and-root for Suite-mediated sync

**Implemented as described in this section.** `AuthDbSetRoot` additionally now absorbs
`AuthDbApplyOfflineOperations`'s replay step in the same call (an `operations` field, verified with
the shared `_replay.py` logic also used by `AuthDbApplyOfflineOperations`) — see `docs/authdb.md`'s
`AuthDbSetRoot` section for the shipped shape; that particular addition was not anticipated by this
proposal document but builds directly on the leaf counter described below.

### The user's target architecture

A single Suite-side database, **global with respect to `device_id`** (one shared database and tree
per wallet, not one silo per physical unit) and **segregated with respect to `wallet_id`** (each
wallet — including each hidden wallet — gets its own tree/rows, never colliding with another). For
the same `device_id`, Suite can always reconstruct the correct Merkle tree; once a Trezor that was
offline is synchronized, it shares the same database with every other synchronized Trezor for that
wallet. An unsynchronized Trezor only needs to (a) update to the latest root, (b) insert its
offline queue into the tree, and (c) send the result to the database so others see the latest
state.

This is already close to what the shipped protocol enables, since `wallet_id` is
seed+passphrase-derived (`core/src/apps/authdb/__init__.py:22-44`) and `mac_key` is wallet-scoped —
every physical Trezor unlocking the same wallet already produces interoperable attestations. What's
missing is (a) a protocol-level primitive for detecting *which address* conflicts when two devices'
offline edits collide, and (b) making the DB's partitioning strategy and its consequences explicit.

### What the root-level counter already does vs. what's missing

The `_ROOTS` counter is a **tree-generation number**: it answers "has anything in this wallet's
tree changed since I last looked," which is exactly what `AuthDbFastForwardRoot`'s monotonicity
check needs. It says nothing about *which* address changed, so it cannot by itself resolve "two
devices each queued an edit to the same address — which one is authoritative?" That is a per-key
question, not a whole-tree one, and no existing primitive answers it.

### Proposed change: an explicit per-leaf version counter, bound into the leaf hash

- New leaf preimage:
  `leaf_hash(address, counter, value) = sha256d(0x00 || address || counter(4B BE) || value)`,
  replacing today's `sha256d(0x00 || address || value)` (`core/src/apps/authdb/_mpt.py:22-23`).
  `counter` becomes a first-class, cryptographically-committed field instead of text an application
  happens to embed inside the opaque `value` blob.
- Semantics: INSERT sets `counter = 1`. UPDATE requires `new_counter == old_counter + 1`, checked
  device-side rather than merely documented. DELETE's virtual-node semantics are unchanged (empty
  value ⇒ excluded from the leaf set; the counter becomes irrelevant once a leaf is virtual).
- Wire shape this would require (not a proto change in this pass — see the itemized table below):
  `AuthDbUpdateLeaf` / `AuthDbOfflineOperation` / `AuthDbRebasedOperation` would gain
  `optional uint32 old_counter` (absent/0 on INSERT) and `required uint32 new_counter`, so the
  device can reconstruct both `leaf_hash(..., old_counter, old_value)` for the membership proof and
  `leaf_hash(..., new_counter, new_value)` for the new leaf, and enforce the `+1` rule.
  `AuthDbLookup` would gain a `counter` field alongside `value`, since membership-proof
  verification now depends on it too.
- This is a **breaking change** to the leaf-hash preimage. It must land before AuthDB ships to any
  production release, or be explicitly versioned (e.g. a new message/field that opts into the
  counter-aware hash, with the old preimage retained for compatibility) if it cannot.
- The root-level counter is **kept exactly as-is**. The two now serve clearly distinct purposes and
  should be named distinctly in documentation going forward: "root counter" (tree generation,
  already shipped) vs. "leaf counter" (per-address version, proposed here) — the current single
  word "counter" is about to become ambiguous once both exist.

### Suite DB architecture: global per `wallet_id`, not per `device_id`

- Partition Suite's `EntryDB`/`RootEntryDB` by `wallet_id`, **not** `device_id`. Since every
  physical Trezor unlocking a given wallet already produces interoperable attestations, the
  database should reflect that with one shared tree per wallet, not one silo per device. `device_id`
  is retained only as a **provenance column** on individual not-yet-merged queue rows (an `EntryDB`
  layout of `[device_id:32][wallet_id:32]...`, per the earlier evaluation's schema sketch) — it
  answers "which physical unit produced this pending op," not "which tree does this belong to."
- **A concrete gap worth flagging explicitly:** the on-device `_SYNC` sequence counter
  (`storage/authdb.py:263-336`, `next_sequence`/`last_applied_sequence`) is **per-device**, not
  per-wallet-global. If the same wallet is loaded on three physical Trezors, each device's sequence
  numbering starts independently at 1 — device A's queued op #1 and device B's queued op #1 are
  unrelated operations that happen to share a sequence number. Global ordering across devices is
  **not** recoverable from sequence numbers alone; it has to be established by Suite itself, as the
  order in which it admits each device's drained queue into its canonical database. This corrects
  an easy but wrong assumption that per-device sequence numbers compose into a global order.
- End-to-end flow for an unsynchronized device, matching the target architecture above, annotated
  with where the new leaf counter changes anything:
  1. Device fast-forwards to Suite's last-attested `(root, counter, mac)` for its `wallet_id` via
     the existing `AuthDbFastForwardRoot` — already production-safe, already cross-device portable,
     **no changes needed here**.
  2. Device drains its local queue via `AuthDbGetOfflineOperations`.
  3. Suite rebases each queued op against its canonical per-wallet tree. **New:** Suite can now
     cheaply pre-check each op's `old_counter` against its own stored per-address leaf counter
     *before* attempting a proof rebase — if Suite's counter for that address is already ≥ the op's
     `old_counter`, the op is stale/conflicting, and Suite applies a resolution policy (reject,
     last-writer-wins, or surface to the user) instead of only discovering the conflict when a
     Merkle proof fails to verify on-device.
  4. Suite calls `AuthDbApplyOfflineOperations` with fresh proofs and old/new counters against
     current canonical state; the device applies and returns a new attested root (mechanism
     unchanged from today).
  5. Suite persists the new canonical root/counter and the per-address leaf counters; other devices
     later fast-forward to it.
- This partially resolves the open question already flagged in `docs/authdb.md` under
  "Fast-forward" (queued ops surviving a fast-forward that raced ahead of them): the leaf counter
  doesn't make the conflict impossible, but it gives Suite a structured, per-address signal to
  detect and resolve it instead of an opaque proof-verification failure.

### Concrete implementation changes required (Part 1)

| Component | File(s) | Change needed |
|---|---|---|
| Leaf hash preimage | `core/src/apps/authdb/_mpt.py:22-23` | `leaf_hash(address, value)` → `leaf_hash(address, counter, value)`; preimage becomes `0x00 \|\| address \|\| counter(4B BE) \|\| value`. `internal_hash` unchanged. |
| Proof verification | `core/src/apps/authdb/_mpt.py` (`verify_proof`, `verify_nonmembership`, `compute_new_root`) | Every call site that builds a leaf hash from `(address, value)` must thread `counter` through too; `compute_new_root`'s UPDATE branch must additionally enforce `new_counter == old_counter + 1` and reject otherwise (new `DataError`); INSERT enforces `new_counter == 1`. |
| `AuthDbLookup` / `Response` | `common/protob/messages-authdb.proto` | Add `optional uint32 counter` (leaf counter, sibling to `value`) to the request; membership check now needs it to reconstruct `leaf_hash`. |
| `AuthDbUpdateLeaf` / `Response` | `common/protob/messages-authdb.proto`, `core/src/apps/authdb/update_leaf.py` | Add `optional uint32 old_counter` (absent/0 = INSERT) and `required uint32 new_counter` to the request; handler passes both into `_mpt.compute_new_root`/leaf-hash calls instead of today's `(old_value, new_value)`-only calls. |
| `AuthDbOfflineOperation` (embedded) | `common/protob/messages-authdb.proto`, `core/src/apps/authdb/queue_offline_operation.py` | Add the same `old_counter`/`new_counter` fields; the queue-time MAC preimage (`HMAC(key, sequence \|\| old_leaf_hash \|\| new_leaf_hash)`) binds counters transitively via the leaf hashes — no separate counter field needed inside the MAC itself. |
| `AuthDbRebasedOperation` (embedded) | `common/protob/messages-authdb.proto`, `core/src/apps/authdb/apply_offline_operations.py` | Same field additions; the per-op MAC/proof reconstruction must use the counter-aware leaf hash. |
| `_ROOTS` storage layout | `core/src/storage/authdb.py:16-23` | **No change.** The root-level counter record is untouched — it's a distinct concept (tree generation) from the new leaf counter, which lives only inside leaf hashes/proofs, never persisted as a separate on-device table (the device only ever checks `new_counter == old_counter + 1` transiently during a single update, using the caller-supplied `old_counter` that the proof already verifies belongs to the current tree). |
| Terminology | `docs/authdb.md` "Counter" section | Disambiguate "root counter" (tree generation, shipped) vs. "leaf counter" (per-address version, proposed) once both exist. |
| Suite-side `EntryDB`/`RootEntryDB` | Suite repository (out of firmware scope) | Partition key `wallet_id`, not `device_id`; `device_id` becomes a provenance column on not-yet-merged queue rows only; add a per-`(wallet_id, address)` leaf-counter column so Suite can pre-check staleness before attempting a proof rebase. |
| Bug fix (prerequisite, unrelated to sync design) | `core/src/apps/authdb/__init__.py:47` | `_derive_mac_key()` must accept the purpose-domain bytes already passed at every call site and mix them into derivation, so `root_mac` and `leaf_approval` keys actually differ. |
| Bug fix (prerequisite, unrelated to sync design) | `core/src/apps/authdb/set_root.py:31-33` | Align its (debug-only) MAC preimage to the `wallet_id \|\| counter \|\| root` shape used elsewhere, so tokens are interchangeable. |

---

## Part 2 — fully offline Bluetooth peer-to-peer sync

**This section is documentation only and introduces no new proto messages, storage layouts, or
firmware handlers beyond Part 1, and no breaking changes.** Every capability BLE peer sync needs is
either already shipped today or already covered by Part 1's additive fields; where a genuine gap
exists, it is recorded as an open limitation for host/relay-side software or the BLE transport
owner, not designed around with new firmware surface.

Scenario: two Trezors that both hold offline edits, connecting to each other directly over
Bluetooth with no Suite database reachable by either side — including the case of "same leaf data
but different counter," where both devices independently edited the same address since a common
ancestor root and must merge without a central arbiter.

- **Attestation portability — already works today, zero changes.** `AuthDbFastForwardRoot`'s MAC is
  `HMAC(wallet-derived mac_key, wallet_id || counter || new_root)`, computable by any device
  holding the wallet, since the key derives purely from seed/passphrase — not a device secret or a
  Suite-held secret. Two Trezors over BLE can verify each other's root attestations with zero
  additional pairing-secret/PKI setup, using the exact RPC that ships today. This is fully
  sufficient for the "one side is a strict superset of the other" case.
- **Queue exchange and replay — already covered by Part 1, no new core surface.** The same
  `AuthDbGetOfflineOperations` → (compare) → `AuthDbApplyOfflineOperations` pair Part 1 proposes for
  Suite-mediated sync is transport-agnostic; neither message assumes the caller is Suite
  specifically. Over BLE, whichever side (or a companion app bridging both BLE links) plays the
  "host" role for a given exchange calls the identical RPCs against each device in turn. No new
  message pair is introduced for BLE.
- **Divergent-branch merge policy — pure host/relay-side logic, no on-device change.** When both
  devices hold offline edits to the same address since a common ancestor root, the merge decision
  lives entirely in whatever software orchestrates the exchange (a companion app, or one Trezor's
  paired phone app relaying to the other): it reads both sides' `new_counter` via the existing
  `AuthDbGetOfflineOperations` response (Part 1), picks a winner (higher counter), and submits only
  the winning op via the existing `AuthDbApplyOfflineOperations`. Part 1's device-side
  `new_counter == old_counter + 1` check is sufficient to reject a losing op outright if it is
  submitted anyway, since its `old_counter` will no longer match the post-merge tree state — **no
  additional on-device conflict-resolution logic is required.** Two sub-questions remain open,
  purely as host-side product decisions, not firmware work:
  1. **True ties** — both branches independently compute the same `new_counter` from a shared base
     (e.g. both compute `old_counter + 1 = 5`). Resolved by whatever deterministic rule the
     orchestrating software picks (e.g. lexicographic comparison of the two candidate MACs); this
     is a relay/app-level policy choice, not something the device enforces differently.
  2. **Losing side's data** — whether the orchestrating software discards the losing op, re-queues
     it against the merged tree with a freshly-read `old_counter` (an ordinary
     `AuthDbQueueOfflineOperation` call, unchanged), or surfaces it to the user for manual
     resolution.
- **Device-to-device session/orchestration (who plays "host") — explicitly out of AuthDB's scope.**
  This is a BLE-transport/session question, not an AuthDB protocol question — AuthDB's RPCs are
  already agnostic to caller identity. BLE session/pairing establishment must be designed by the
  BLE transport owner; AuthDB's contract ends at "the existing RPCs work over whatever
  authenticated BLE session already exists."
- **Security note, not a change.** AuthDB's MACs are transport-independent and verified on-device
  regardless of channel, so the crypto model already carries over to BLE unchanged. The BLE
  transport/security owner should separately confirm no implicit "wired = physically present" trust
  assumption elsewhere in the codebase is violated by BLE's different threat model (longer range,
  weaker physical-presence guarantee than USB) — out of scope for this proposal to resolve, and not
  something that requires an AuthDB change.

### Summary table (Part 2)

| Component | Firmware/proto change needed | Status |
|---|---|---|
| Cross-device attestation verification | None — `AuthDbFastForwardRoot`'s wallet-derived `mac_key` already lets any device holding the wallet verify another device's attestation with no shared secret beyond the seed/passphrase. | Ships today, reuse as-is. |
| Queue exchange + replay | None — reuses Part 1's `AuthDbGetOfflineOperations` / `AuthDbApplyOfflineOperations` verbatim; both are already transport- and caller-agnostic. | Covered by Part 1, no new surface. |
| Divergent-branch merge decision (which side wins) | None on-device — pure host/relay-side policy reading `new_counter` from the existing `AuthDbGetOfflineOperations` response (Part 1); the device-side `new_counter == old_counter + 1` check already rejects a losing op if resubmitted. | Host/relay-side logic only; open product questions (tie-break rule, losing-op handling), not firmware work. |
| Device-to-device session/orchestration (who plays "host") | None in AuthDB — belongs entirely to the BLE transport/session layer; AuthDB's RPCs are already agnostic to caller identity. | Explicitly out of AuthDB's scope — a BLE-transport-owner item. |
| BLE transport security review | None in AuthDB (MACs are already transport-independent) — confirm no *other* code path assumes USB-level "wired = physically present" trust that BLE's threat model would violate. | Out of scope for this document — flag for the BLE transport owner. |

---

## Part 3 — conflict display: cross-device history for an address

**Design spec only — Suite-side, not implementable in this repository.** The device never retains
a "previous canonical root" or any history: only the current `root`/counter and its own
not-yet-garbage-collected offline queue. "What happened on this address, on every Trezor, since
the last canonical root" is not a question firmware can answer alone — it requires an **append-only
log of applied operations**, which only Suite can hold, since only Suite ever observes every
device's queue contents (via `AuthDbGetOfflineOperations`) before rebasing and replaying them.

The good news: firmware already exposes everything the log needs, with **no firmware or protocol
change required**:

- `AuthDbGetOfflineOperations` already returns each queued operation's `address`, `old_value`,
  `new_value`, and (per Part 1) `old_counter`/`new_counter`.
- Each batch can already be attributed to the specific physical Trezor that produced it via
  `Features.device_id` of the connection that uploaded it — no AuthDB-specific device identifier is
  needed for attribution, since `Features.device_id` is already exposed today.
- `AuthDbApplyOfflineOperationsResponse`/`AuthDbSetRootResponse` already return the root-level
  `counter` reached immediately after each applied op, giving a stable point to anchor a history
  entry to ("this op landed when the tree's root counter became N").

What's missing is Suite *retaining* this as a durable, queryable log instead of discarding it after
each apply — that's the only piece this section designs.

### Proposed Suite-side schema/functions

```
# Called once per successfully-applied operation, at the same time Suite persists the new
# canonical root/counter reached by that operation (i.e. right after each AuthDbApplyOfflineOperations
# or AuthDbSetRoot call that reports applied_count > 0, once per applied op in the batch):
record_history_entry(
    wallet_id, address, device_id,        # device_id = Features.device_id of the uploading connection
    old_value, new_value,
    old_counter, new_counter,             # from Part 1's leaf counter, threaded straight through
    applied_at_root_counter,              # the wallet's root-level counter value right after this op
)

# "What changed on address X between two canonical states":
get_address_history(wallet_id, address, since_root_counter, until_root_counter)
    -> ordered list of (device_id, old_value, new_value, old_counter, new_counter, applied_at_root_counter)
```

`get_address_history` is what lets a UI answer "what happened on all Trezors since the last
canonical root I saw" for one address: `since_root_counter` is the counter the caller last observed
(e.g. from its own last `AuthDbLookup`/`AuthDbGetOfflineOperations` call), `until_root_counter` is
the wallet's current counter, and the ordered result is exactly the sequence of writes — each
tagged with which physical device produced it — that moved the address from its old state to its
current one.

### Why this is out of firmware/this-repo's scope

This is a schema/function-signature design, not code that can land in `trezor-firmware`. It belongs
in the Suite repository (the host application holding the canonical database), which was not added
to this session (`trezor/trezor-firmware` only) — implementing `record_history_entry`/
`get_address_history` for real requires that repository and is tracked as separate follow-up work.

---

## File index

| File | Description |
|---|---|
| `docs/authdb.md` | Shipped AuthDB protocol, wire messages, and security notes |
| `common/protob/messages-authdb.proto` | Protobuf message definitions (Part 1's leaf-counter fields are shipped) |
| `core/src/storage/authdb.py` | Persistent storage: `_ROOTS`/`_CACHE`/`_QUEUE` (the old `_SYNC` sequence-reservation table was removed; next sequence is now derived, not separately persisted) |
| `core/src/apps/authdb/_mpt.py` | Shared MPT hash/proof primitives, including Part 1's counter-aware leaf hash |
| `core/src/apps/authdb/_replay.py` | Shared offline-op replay loop (extracted so `AuthDbApplyOfflineOperations` and `AuthDbSetRoot`'s embedded replay share one implementation) |
| `core/src/apps/authdb/__init__.py` | `device_id`/`wallet_id`/MAC-key derivation (the prerequisite `_derive_mac_key` bug noted above is fixed) |
