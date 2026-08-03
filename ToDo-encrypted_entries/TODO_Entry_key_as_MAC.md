# WARD: entry_key = HMAC(K_index, scope ‖ identifier) — aligning impl to ward-design.md

> Status: design agreed through the interactive session below; **two open questions remain**
> (K_index granularity + export gating — see Open Questions) before the PUSH/key-export parts are
> implementable. The PULL + entry_key + encrypted-leaf parts are unambiguous.

## Context

`ward-design.md` **already specifies** the change requested here. The shipped implementation
diverged: it uses an *unkeyed* `entry_key = sha256(app_id ‖ 0x00 ‖ type ‖ 0x00 ‖ address)`
(`service.py:86`, host `proof/index.ts:56`) and carries the plaintext `address` on every wire
message, so Suite knows the preimages and can see the structure/count of entries. The design instead
specifies a **keyed** path with the identifier hidden from Suite:

- **§1 / §3.1:** `entry_key = HMAC(K_index, scope ‖ identifier)`, `K_index` a SLIP-21 key under
  `m/"ward"`.
- **§2.5:** this is a **PRF to derive a path, not an authenticator** — it hides the identifier and
  makes the path host-unforgeable; it is *not* proof a write "went through access control" (that stays
  the on-device confirm in `_confirm_update`).
- **§3 (pull-only):** the Trezor computes `entry_key` and asks Suite for that path; "the Suite knows
  `entry_key` but never `identifier`."
- **§5:** per-device records use a device axis inside `scope`, **not** a per-device key — K_index is
  seed-derived and shared. This is the mechanism for "per-device entries without revealing their
  number" (§5.2), the stated motivation.

**Scope composition (resolved):** `scope = app_id ‖ key_type ‖ device_id`, where `device_id = 0x00`
for a global entry, so `entry_key = HMAC(K_index, app_id ‖ key_type ‖ device_id ‖ identifier)`.
`app_id` (domain: bitcoin/ethereum/display_address) moves **into** scope; `key_type` generalizes the
current constant `type = "address"` into an explicit discriminator. **Sub-point to confirm:** §5.1
argues the device axis should be a **user-chosen, reclaimable slot** (0..15, confirmed on screen), not
a hardware- or random-derived id — restoring a seed onto replacement hardware otherwise orphans the
old device's records permanently. Assume `device_id` == that user-chosen slot unless you intend
otherwise.

**This task brings the implementation in line with §1/§3/§5 for the entry_key/path layer**, plus the
minimum of §2.1's encrypted-leaf model needed to support the push variant (below).

## Two access flows

- **PULL (private / per-device, design-canonical):** Trezor computes `entry_key` locally and sends the
  **path (`entry_key`)** in `WARDProofRequest` — never the identifier. Suite looks up the row by
  `entry_key`, returns the proof, and holds no keys. Trezor verifies against its root and decrypts.
- **PUSH (Suite-assisted, deliberate divergence from §0):** Suite **retrieves the necessary keys
  (`K_index`, `K_data`) from the Trezor** so it can compute `entry_key = HMAC(K_index, scope ‖
  identifier)` by identifier and encrypt/decrypt values itself. This lets Suite autonomously locate/
  render entries by their identifier (e.g. coin-address labels). Suite holds the retrieved key
  **in memory only (session-scoped, never persisted)**. It knowingly downgrades the §0 "Suite holds no
  keys" property **for the push-capable class only** — see Open Questions for the remaining granularity
  bound.

## Open questions (resolve before implementing the PUSH/key-export parts)

**Resolved:** scope composition (= `app_id ‖ key_type ‖ device_id`); key export is in-memory/
session-scoped only; leaf encoding = full §2.1/§2.2 encrypted leaf; `K_data` is per-`entry_type`;
`entry_type` in the clear; `entry_key` in the clear.

1. **Key export (PUSH).** Exported capability = **`K_index` (construct `entry_key`) + `K_data`
   (decrypt `entry_value`) only**, never `K_sig`, so Suite can locate a leaf by identifier and attach
   the correct proof. **`K_data` is per-`entry_type`** (`SLIP-21(K_data_master, key_type)`), so the
   export hands over only the types Suite renders; per-device/private types stay non-decryptable.
   Remaining to confirm: (a) is **`K_index` likewise per-scope** (so Suite can't compute the *paths* of
   non-exported/private scopes, esp. for guessable identifiers), or a single seed-wide index key?
   (b) is the export **user-confirmed** on device?
2. **Internal-node encoding (out of "full leaf"?).** "Full leaf" fixes the leaf/commit. §2.2 also
   defines `internal = H(0x01 ‖ skiplen ‖ left ‖ right)` with path compression + §2.3 canonical-form
   invariants (two non-empty children, maximal skiplen), optionally §3.3 subtree counts. Assumed
   **out of scope** (keep the current internal-node encoding, just swap the leaf) unless the full §2.2
   trie restructure is wanted — device and host must match either way.

## AEAD nonce — RESOLVED (Option 1)

Firmware `trezor.crypto.chacha20poly1305` is **RFC-7539 ChaCha20-Poly1305 with a 12-byte nonce**
(`modtrezorcrypto-chacha20poly1305.h:60`), not XChaCha20. **Decision:** the leaf `salt` becomes a
**12-byte `nonce`** used directly as the RFC-7539 nonce (renamed `salt`→`nonce` in `ward-design.md`
too). Random per write (§4.5); 96-bit birthday bound per `entry_type` key — far beyond any wallet.

## Progress (2026-07-31)

- **DONE + verified (CPython):** `trezor-firmware/python/src/trezorlib/ward_crypto.py` — the canonical
  keyed layout, all asserted:
  - SLIP-21 `K_index` + per-`entry_type` `K_data` derivation (matches `apps.common.seed.Slip21Node`).
  - `entry_key = HMAC-SHA256(K_index, app_id ‖ 0x00 ‖ key_type ‖ 0x00 ‖ device_id(1B) ‖ identifier)`
    — 32B path; scope separation + unforgeable-without-K_index proven.
  - keyless `commit = SHA-256(0x02 ‖ nonce ‖ tag ‖ len32(ct) ‖ ct)`, `leaf = SHA-256(0x00 ‖ entry_key
    ‖ commit)`.
  - leaf codec `encrypt_leaf`/`decrypt_leaf` (RFC-7539 ChaCha20-Poly1305, 12B nonce, AAD
    `0x02 ‖ entry_key ‖ entry_type`, plaintext `C_leaf ‖ len16(id) ‖ id ‖ len32(value) ‖ value`,
    bucketed 64/256/1024/4096B): round-trip, AAD/type binding, tamper rejection, random-nonce
    uniqueness all pass.
  - Frozen vectors (seed=00*64): K_index `1f3cab97…`; entry_key btc/alice `29e70899…`;
    commit(nonce=01*12,tag=02*16,ct="cipher-bytes") `bdf66a0c…`.
- **DONE + verified (CPython):** `authdb_tree.py` refactored to commit-based & key-first
  (`_leaves: entry_key → (nonce,tag,ct)`; `set_leaf`/`del_leaf`/`get_leaf`; `get_proof_by_key`,
  `get_nonmembership_proof_by_key` → `(proof, witness_entry_key, witness_commit)`;
  `verify_proof_by_key`, `verify_nonmembership_by_key`). Persisted unit tests
  `python/tests/test_ward_crypto.py` (6 pass) cover membership/non-membership/empty/delete **and the
  wrong-key + fabricated-key negatives** (the flagged gap).
- **DONE + verified (CPython):** proto `messages-ward.proto` updated — `WARDProofRequest.address`(1)→
  `entry_key`(4); `WARDProofAck`/`WARDLookup` `value`+`counter`→`entry_type/nonce/tag/ct`,
  `witness_value_hash`→`witness_commit`; `WARDQueueUpdate` gains `key_type`+`device_id`. Regenerated
  **both** binding sets (`core/src/trezor/messages.py` + `python/src/trezorlib/messages.py`) via
  `tools/build_protobuf` (protoc from nix store `8sbmq3x…-protobuf-33.5`, `.venv` on PATH). `ward.py`
  `build_proof_ack`/`tree_proof_callback` now key-first (`msg.entry_key`), `lookup`/`queue_update`
  threaded. Exercised end-to-end in CPython (membership decrypt, non-membership witness, wrong-key
  negative). Connect buf regen still pending (needs buf).
- **DONE (firmware; py_compile-clean, emulator validation pending):** `apps/ward/service.py`
  (keyed `entry_key`, `commit`/`leaf`, streaming ChaCha20-Poly1305 `encrypt_leaf`/`decrypt_leaf`,
  `K_index`/per-type `K_data` via `Slip21Node`, `verify_proof`/`verify_nonmembership`/
  `compute_new_root` on the commit model, `entry_key_for`, `export_keys` + confirm); `apps/common/ward.py`
  (PULL sends `WARDProofRequest(entry_key=…)`; `lookup`/`resolve_label`/`verify_label`/`lookup_label`
  key-first; `export_keys`); handlers `queue/lookup/perform/export_keys` + `workflow_handlers`;
  **write-flow leaf-return** added to `WARDPerformUpdateAck` (entry_key/entry_type/nonce/tag/ct) so the
  host can store the leaf it can't compute; `WARDExportKeys`/`Ack` added (id 2352/2353). Display PUSH
  path migrated: `messages-bitcoin.proto GetAddress` + `messages-display_address.proto
  DisplayAddressWithProof` (value/counter→entry_type/nonce/tag/ct, witness_value_hash→witness_commit),
  `bitcoin/get_address.py`, `display_address/show_with_proof.py`; `show.py` (PULL) already compatible.
  Both firmware+trezorlib bindings regenerated. **Interim limitation:** `key_type`/`device_id` default
  to "address"/0 (not yet persisted in the pending record — `ward_store` framing unchanged).
- **connect binding regen DONE (2026-08-01):** ran `buf generate` against the LOCAL firmware protos
  (the repo's `scripts/protobuf-build.sh` clones upstream `main`, so instead: copied
  `trezor-firmware/common/protob/*.proto` → `packages/protobuf/scripts/build/`, `rm` webauthn/
  benchmark/nem/nostr, `BUF_CACHE_DIR=$TMPDIR/bufcache buf generate` from `scripts/`, then the perl
  comment-strip + `.js`-import + `mv messages-thp_types.ts → protocol` post-steps). Verified
  `messages-ward.ts` + `_pb.js` fileDesc carry `entry_key`(required, no address)/`entry_type`/
  `nonce`/`tag`/`ct`/`witness_commit`/`key_type`/`device_id`/`WARDExportKeys`. **This fixes the
  `WARDProofRequest.address required` encode error.** (eslint/prettier not run — cosmetic.)
- **NEXT — connect LOGIC (TS; the remaining work; needs jest to validate):** KEY FINDING —
  `wardUpdate` pre-builds the proof from the address (`toProofAck(change.oldProof, appId)`) and returns
  it fixed in the `perform` callback. The host can no longer compute `entry_key` from the address (no
  K_index in pull), so the proof must be built **reactively from `request.entry_key`** inside the
  callback. Migration: (a) `@trezor/ward` — key the host tree by `entry_key` (opaque), store the
  encrypted blob `(nonce,tag,ct,entry_type)`, build membership/non-membership proofs BY entry_key,
  commit=`sha256(0x02||nonce||tag||len32(ct)||ct)`, leaf=`sha256(0x00||entry_key||commit)` (mirror
  `trezorlib/authdb_tree.py` + `ward_crypto.py`); (b) `wardSession.perform` — set the proof callback to
  build the ack from `request.entry_key` (not a pre-built fixed ack); (c) `wardUpdate` — after
  perform/confirm, store the leaf blob the device returned in `WARDPerformUpdateAck` keyed by its
  `entry_key`; (d) `proofAck.ts` — emit `entry_type/nonce/tag/ct` + `witness_commit`; (e) `wardLookup`/
  `wardVerify`/`wardDisplayAddress` + connect-common types; (f) optional `export_keys` client + K_index/
  K_data-based path computation for the PUSH (label-render) flow only.
- **NEXT — device tests / harness (emulator-gated):**
  1. Firmware `apps/ward/service.py` — mirror `ward_crypto.py` exactly:
     - `entry_key()` → `HMAC-SHA256(K_index, app_id||0x00||key_type||0x00||device_id(1B)||identifier)`;
       replace `value_hash`/`leaf_hash` with `commit_of(nonce,tag,ct)=sha256(0x02||nonce||tag||
       len32(ct)||ct)` and `leaf_hash_of(entry_key, commit)`.
     - `verify_proof(entry_key, nonce, tag, ct, proof, root)`, `verify_nonmembership(entry_key,
       witness_entry_key, witness_commit, proof, root)`, `compute_new_root(... nonce/tag/ct ...,
       witness_commit)` — swap `(counter,value)`→`(nonce,tag,ct)`; C_leaf now inside `ct`, enforce
       `C_new>C_old` by decrypting pre-state.
     - Add `K_index`/`K_data(key_type)` via `Slip21Node` (`apps/common/seed.py`): paths
       `[b"ward", b"K_index"]` and `[b"ward", b"K_data", key_type]`.
     - AEAD: firmware `trezor.crypto.chacha20poly1305` is **streaming** —
       `c=chacha20poly1305_encrypt(K_data, nonce); c.auth(0x02||entry_key||entry_type);
       ct=c.encrypt(pt); tag=c.finish()`; decrypt mirrors with `_decrypt`+`c.finish()` compare.
       Plaintext framing `C_leaf(4B)||len16(id)||id||len32(val)||val`, bucket-pad 64/256/1024/4096.
     - Thread `key_type`/`device_id` through `queue`/`perform`/`lookup`/`lookup_label`; **PULL**:
       `apps/common/ward.py` `perform`/`resolve_label` send `WARDProofRequest(entry_key=…)` (compute
       in service where the seed lives, hand to TC before `context.call`).
     - `storage/ward_store.py` pending record: frame `key_type`/`device_id` alongside `app_id`.
  2. Host TS `packages/ward` — **needs suite monorepo build.**
  3. Device tests `tests/device_tests/misc/test_ward*.py` + `ward_mgr_emu.py` — rework to the key-first
     tree (old plaintext `insert(app_id,address,value)` / `get_value` API removed) — **emulator-gated.**
  4. Connect buf regen for `messages-ward` (+`messages-display_address` if touched) — **needs buf.**
  5. PUSH `WARDExportKeys` — still blocked on the 2 open questions (K_index granularity + export
     confirmation).

## Round 2 fixes (2026-08-01, from emulator + pytest logs)

- **CONFIRMED:** firmware sends `WARDProofRequest(entry_key)` on the emulator (fix works).
- **connect `ward_proof` encode error FIXED:** my first regen added the WARD PUSH fields to the shared
  bitcoin `GetAddress`; proto2 `repeated ward_proof` → a **required** array that connect's internal
  `getAddress` (DeviceCommands/validateState, run for every method) never sets → every Suite flow
  failed. Removed the WARD fields from `GetAddress` (`messages-bitcoin.proto` → `reserved 8/9/10`) and
  the firmware `bitcoin/get_address.py` ward block (the label-on-address feature lives in
  `DisplayAddress`/`DisplayAddressWithProof`). Regenerated firmware + connect bindings; `GetAddress`
  now has no ward fields.
- **DisplayAddress no-screen HARDENED (`display_address/show.py`):** added `log.debug`/`log.warning`
  tracing and broadened the label-resolution guard from `except DataError` to `except Exception` —
  ANY failure now logs + shows an on-device warning and STILL shows the address, never a blank/aborted
  flow. Added pull-path tracing in `common/ward.py resolve_label` (entry_key pull + ack membership/
  witness).
- **`WARDTree` convenience API restored (`trezorlib/authdb_tree.py`):** `insert`/`delete`/`get_value`/
  `get_counter`/`get_proof`/`get_nonmembership_proof`/`leaf_blob`, keyed by a tree-held
  `(k_index, k_data)` (defaults derived from a fixed test seed). Sync tests (device ADOPTS the root)
  work with defaults; pull/verify tests MUST construct `WARDTree(k_index, k_data)` from the device's
  keys. Verified in CPython.
- **`ward_mgr_emu.device_ward_keys()` added + `test_ward_sync.py` REWORKED (py_compile + import
  clean; emulator run pending):** `device_ward_keys(key_type)` reproduces the device's `K_index`/
  `K_data` from the known "all all all" seed (SLIP-21, byte-parity with `ward_crypto` verified). Tests
  build the host tree via `WARDTree(_K_INDEX, _K_DATA)` (helper `_tree()`), and a `_lookup()` helper
  issues the new `ward.lookup` (leaf blob `nonce/tag/ct` + proof). This is the MODEL for the other two
  files. → run `pytest tests/device_tests/misc/test_ward_sync.py -q` to confirm.
- **`test_ward_sync.py` GREEN (10 passed on emulator).** `test_ward.py` + `test_display_address.py`
  REWORKED the same way (py_compile + parse clean; emulator run pending):
  - device keys via `device_ward_keys()` + `_tree()`; `ward.lookup` calls → `_lookup_membership`
    (leaf blob `nonce/tag/ct`) / non-membership `witness_commit`.
  - **Write round:** `ward.perform_update` now returns the device's leaf blob
    (entry_key/entry_type/nonce/tag/ct); the harness stores THAT blob via `_apply_device_leaf`
    (random nonce ⇒ host must not re-encrypt or roots diverge). Removed the manual `tree.insert/delete`
    after edits (the round helper syncs the tree).
  - **PUSH display:** `DisplayAddressWithProof` built via `_with_proof(tree, address, proof)` (blob +
    proof) instead of `value`/`counter`.
  - Obsolete "stale counter" WARDLookup sub-check dropped (C_leaf is inside `ct` now). Skipped
    `test_ward_get_address_label` left as-is (getAddress WARD fields removed).
- **CONNECT MIGRATION DONE (code-complete; needs a clean monorepo rebuild to type-check/run):**
  diagnosis was — 1st write (empty tree/INIT) succeeded, but every subsequent write failed with
  `witness_commit=None` / `witness_entry_key/witness_commit required for INSERT` → "database not
  updated", because connect's `@trezor/ward` still used the old plaintext model. Migrated:
  - `packages/ward/proof/index.ts`: `commitOf`/`leafFromCommit` + `BlobRow` + `computeRootFromBlobs`/
    `proofByKey`/`nonMembershipByKey` (serve proofs BY the device's entry_key over stored blobs).
    TS crypto verified byte-identical to trezorlib vectors (commit `bdf66a0c…`, leaf `9c4aa1d3…`).
  - `types` (`WardLeafBlob` + `WardEntry.blob`), `app` (`blobRows`, `commitLocal` persists blob),
    `storage` in-memory (stores whole entry) + sqlite (new nullable `blob` JSON column + ALTER
    migration; lookup/upsert/getAllEntries read/write it).
  - connect `proofAck.ts` → `buildAckByKey(rows, entryKeyHex)` (membership entry_type/nonce/tag/ct;
    non-membership witness_entry_key/witness_commit); `wardSession.perform`/`displayAddress` take a
    reactive `buildAck(request)` and `perform` returns the device leaf blob; `wardUpdate` serves by
    `req.entry_key` + stores the returned blob via `commitLocal`; `wardDisplayAddress` reactive;
    `wardVerify` membership-via-blob (non-membership PUSH degrades — host can't compute the target
    entry_key); `wardLookup` raw params updated to nonce/tag/ct/witness_commit.
  - `@trezor/ward` tsc PASSES. connect tsc still shows stale-dep errors ("new field missing on OLD
    type") until a clean rebuild — **REBUILD ORDER: @trezor/protobuf → connect-common → @trezor/ward →
    @trezor/connect** (I rebuilt protobuf/ward/connect-common libs; connect project-ref cache is
    stale). Runtime already uses the new fields (log shows entry_key/witness_commit).
- **STILL: ward_store per-type/device framing; full clean rebuild to confirm connect Suite flow.** two remaining changes per file: (1) the host tree must
  use the DEVICE's keys so entry_keys match — either `ward.export_keys(session,"address")` (needs the
  export confirm handled by a device handler) OR derive `k_index`/`k_data` from the known emulator seed
  via `ward_crypto`; (2) update `ward.lookup(...)` call sites to the new signature — pass the leaf blob
  (`tree.leaf_blob(...)` → nonce/tag/ct) instead of `value`/`counter`, and `witness_commit` instead of
  `witness_value_hash`. `test_ward` also stores the leaf blob returned in `WARDPerformUpdateAck`.

## Leaf encoding (§2.1/§2.2, with a per-type-key divergence)

- **Per-type `K_data`:** `K_data(key_type) = SLIP-21(K_data_master, key_type)` under `m/"ward"` — a
  **separate decryption key per entry type**. Trezor is the encryptor (§4).
- **Plaintext (outside `ct`):** `entry_key` (the trie path — never encrypted), **`entry_type`**,
  `salt`, `tag`, `len(ct)`.
- **Divergence from §2.1:** `entry_type` is in the **clear**, because the type must be known to select
  `K_data(key_type)` before decrypting. §2.1 deliberately put `leaf_type` *inside* `ct` to stop the
  relay/Suite from category-partitioning and per-type edit-frequency counting; per-type keys re-open
  that leak. **Accepted trade** (documented, not an oversight). `entry_type` == `key_type` in the
  `entry_key` preimage, so it is already bound into the path; also bind it into the AEAD AAD.
- `ct = AEAD_enc(K_data(key_type), nonce=salt, aad = 0x02 ‖ entry_key ‖ entry_type,
  plaintext = C_leaf ‖ identifier ‖ value ‖ padding)`, padded to length buckets
  (64/256/1024/4096 B, §2.1/§4.4). (`leaf_type` removed from `ct` — now the clear `entry_type`.)
- `salt` = random 24 B (per write, never derived — §4.5 nonce-reuse hazard). `tag` = 16 B Poly1305.
- `commit = H(0x02 ‖ salt ‖ tag ‖ len32(ct) ‖ ct)`; `leaf = H(0x00 ‖ entry_key ‖ commit)`.
- **`C_leaf` lives inside `ct`**, not on the wire. Counter-monotonicity (`C_new > C_old`) is enforced
  by the *signing* device decrypting the pre-state proof at write time (§4.5). Deletes: `len(ct) = 0`
  → `empty` sentinel (§7).

---

## Firmware (`trezor-firmware/core/src/apps/ward/`)

1. **Key hierarchy (align to §1).** Add SLIP-21 derivations for `K_index` (HMAC key) and `K_data`
   (XChaCha20-Poly1305 key) under `m/"ward"`, alongside the existing `_get_ward_id`/`_derive_mac_key`
   (`service.py:345,366`) → reconcile naming to the design's `K_sig`/`K_index`/`K_data`. `K_data` is
   needed on **both** flows (the pull device decrypts too), not just push.
2. **`service.py:86` `entry_key()` → `HMAC(K_index, app_id ‖ key_type ‖ device_id ‖ identifier)`.**
   Async-key refactor: derive `K_index` once per operation and thread it into `entry_key(...)` — don't
   make `entry_key` async at every call site (`:556` `lookup_label`, `:720` `lookup`, `:819`
   `perform`). `witness_entry_key` stays opaque.
3. **Leaf → §2.1/§2.2 (see "Leaf encoding").** Replace `value_hash(counter,value)` / `leaf_hash`
   (`service.py:104-120`) with `commit = H(0x02 ‖ salt ‖ tag ‖ len32(ct) ‖ ct)` and
   `leaf = H(0x00 ‖ entry_key ‖ commit)`. `verify_proof` (`:145`) forms the leaf from `(salt,tag,ct)`
   instead of `(counter,value)`; `verify_nonmembership` (`:160`) and `compute_new_root` (`:190`) take a
   `witness_commit` in place of `witness_value_hash` (still opaque). Add AEAD encrypt/decrypt helpers
   (`trezor.crypto` XChaCha20-Poly1305) with AAD `0x02 ‖ entry_key ‖ entry_type`; on the write path
   decrypt the pre-state and enforce `C_new > C_old` (§4.5). `reconstruct`/`internal_hash` unchanged
   (OQ #2).
4. **PULL request carries the path.** In `apps/common/ward.py`, the `perform` pull
   (`WARDProofRequest`, ~`:229`) and `resolve_label` pull (~`:141`) send **`entry_key`**, not
   `address`. The key needs the seed → compute in `service` (seed access) and hand to the TC gateway
   before `context.call` (keep TW = no wire I/O). Add a service helper (`entry_key_for(pending_id)` /
   `entry_key(app_id, key_type, device_id, identifier)`).
5. **Device-id in scope (§5).** `device_id = 0x00` for global; otherwise a user-chosen, reclaimable
   slot captured/confirmed at setup and stored (§5.1 — not hardware/random). Thread it into the
   entry_key preimage. (Setup-probe warning for slot collision per §5.1 is a follow-up.)
6. **PUSH key export.** New gated wire op (e.g. `WARDExportKeys`) returning `K_index`(/`K_data`) subject
   to OQ #1 (granularity, confirm). In-memory/session-scoped on the host. Must be a dedicated,
   confirmed export — never a generic "sign/derive arbitrary" API (§1 discipline note).

## Wire / proto (`common/protob/messages-ward.proto`)

- **`WARDProofRequest`**: field 1 `address` → `entry_key` (bytes); `app_id`(3) folded into the key,
  drop/reserve; keep `pending_id`(2).
- **`WARDProofAck` / `WARDLookup`**: replace plaintext `value` + `counter` with the leaf blob
  `entry_type`(clear) / `salt`(24 B) / `tag`(16 B) / `ct`; rename `witness_value_hash` →
  `witness_commit`. Membership sets these; the device selects `K_data(entry_type)` and decrypts to
  recover value + `C_leaf`.
- **`WARDQueueUpdate`**: `new_value` stays plaintext at queue (the value the user confirms); the
  device encrypts it to `salt/tag/ct` at perform. (For a private per-device entry the value still
  originates from the app via the host at queue time.)
- **New `WARDExportKeys`/`Ack`** for the push key retrieval (OQ #1).
- **Regen ALL THREE bindings** (firmware `build_protobuf`, trezorlib, Connect buf — scoped `--path`,
  restore `index.ts` barrel). Skipping buf silently drops renamed fields (documented gotcha).

## Host reference (`trezorlib`) + Host TS (`packages/ward`)

- **`authdb_tree.py`**: tree already keys `_leaves` by the 32-byte key (`:159`) and has
  `_get_proof_by_key` (`:300`). Add public **key-first** methods (`get_proof_by_key`,
  `get_nonmembership_proof_by_key`, `get_counter/value_by_key`, `insert/delete_by_key`). `ward.py`
  `build_proof_ack`/`tree_proof_callback` (`:223,250`) read `msg.entry_key`.
- **`packages/ward` storage** (`storage/sqlite/index.ts:37-45`, `storage/index.ts:51`,
  `types/index.ts:55`): key rows by `entry_key` (`PRIMARY KEY (ward_id, entry_key)`) and store the
  leaf blob `entry_type`(clear) `/salt/tag/ct` instead of plaintext `value`/`counter` (Suite can no
  longer reconstruct value from `networkSymbol + metadata`). Identifier columns nullable/absent for
  pull-only.
  For PUSH, Suite computes `entry_key` from the exported `K_index` (add `entryKey(kIndex, app_id,
  key_type, device_id, identifier)` taking the retrieved key, replacing the keyless `entryKey` at
  `proof/index.ts:56`) and can decrypt `ct` with the exported `K_data`.
- **`proof/index.ts`**: leaf hashing follows §2.2 (`commit = H(0x02 ‖ salt ‖ tag ‖ len32(ct) ‖ ct)`,
  `leaf = H(0x00 ‖ entry_key ‖ commit)`); `rowsToLeaves` (`:161`) keys by `r.entryKey` over the stored
  blob; add key-first `generateMerkleProof`/`generateNonMembershipProof` taking a `targetKey`;
  non-membership returns `witnessEntryKey`/`witnessCommit`.
- **`app/index.ts` `proofFor`** (`:81`): PULL takes `entryKey`; PUSH computes it from the exported key.
- **connect**: no `WARDProofRequest` handler yet (`ward-proof-on-demand`); Suite-side pull wiring +
  the key-export UX are **follow-up**.

## Tests

- **New negatives (gap flagged; `test_ward.py` only asserts `valid == True` today):** (a) a proof
  built for a *different* `entry_key`/identifier is rejected (`valid == False`); (b) a host-fabricated/
  random `entry_key` cannot pass (`reconstruct != root`).
- **Harness rework** (`test_ward.py WardHostHarness`, `ward_mgr_emu.py`): host tree keys by
  device-supplied `entry_key` (pull) — `ward_proof_callback` reads `entry_key`; for push tests, the
  harness obtains `K_index` via the export op and computes `entry_key` itself.
- **Scope/slot tests:** global vs device-slot entries land on different paths and don't collide (§5.1).
- **Leaf/AEAD tests:** round-trip encrypt→commit→leaf→verify; a tampered `ct`/`tag` fails the AEAD (hard
  abort, §3.1); counter-monotonicity — a spliced older leaf (lower `C_leaf` in `ct`) is rejected at
  write (§4.5); a `len(ct)=0` delete resolves to `empty`.
- Host TS: update `packages/ward` unit tests + `wardMethods/__tests__` fixtures (entry_key column,
  salt/tag/ct blob, key-first proofs, `witnessCommit`); mind the JestCustomEnv `console.error` spy
  gotcha.

## Verification

1. Firmware `py_compile` + CPython: `entry_key` stable per seed/scope; correct proof verifies,
   wrong-key proof rejected; scope prefix separates global/device paths.
2. trezorlib: `build_proof_ack` via `*_by_key` for membership/non-membership/empty verifies against
   root.
3. Host TS: `packages/ward` jest green (entry_key-keyed storage/proofs; push path using retrieved key).
4. Emulator (`xtask build firmware --model t3w1 -e -d --pyopt false`): full PULL-by-entry_key round
   (queue→perform→confirm) and, if built, a PUSH round using exported keys; new negatives fail as
   expected.
5. Regen sanity: renamed `WARDProofRequest.entry_key` + `WARDExportKeys` survive encode/decode across
   all three bindings.
