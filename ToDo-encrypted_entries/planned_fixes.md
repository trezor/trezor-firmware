# WARD keyed-entry_key migration — planned fixes (gaps / degraded / postponed)

Companion to `TODO_Entry_key_as_MAC.md` (the design + what's done) and `ward-design.md`
(the target model). This file tracks everything **missing, degraded, postponed, or
divergent** after the migration to `entry_key = HMAC(K_index, scope ‖ identifier)` with
encrypted leaves, plus the concrete fix for each.

> **Batch-update security review:** the analysis of the proposed batch-update protocol
> (K_head/K_auth MACs, AuthCommit/AuthRevert, forward-increment rollback, dropped
> batch_digest, another-Trezor verification) lives in
> [`batch_update_security_review.md`](./batch_update_security_review.md) — findings F1–F12,
> the `t_anchor`/epoch rationale, and the locked design decisions.

## State of the world (as of 2026-08-02)

- **Firmware**: migrated (keyed entry_key, commit/leaf, ChaCha20-Poly1305 encrypt/decrypt,
  K_index/per-type K_data via SLIP-21, verify/compute_new_root on the commit model, PULL sends
  `WARDProofRequest(entry_key)`, `WARDPerformUpdateAck` returns the device leaf blob, `WARDExportKeys`
  handler). Device tests green on emulator: `test_ward_sync` 10/10, `test_ward` 19/1-skip,
  `test_display_address` 8/8.
- **trezorlib**: migrated + unit-tested (`ward_crypto.py`, `authdb_tree.py` key-first, `ward.py`).
- **connect**: migrated to serve proofs **by the device's entry_key** over stored opaque blobs
  (`buildAckByKey`, reactive `wardSession.perform/displayAddress`, blob persisted in sqlite).
- **Observed on emulator (`ward_tests.log`)**: write (dbchange insert/update/delete) ✅, display
  (dbdisplay membership + **proven** non-membership) ✅, membership dblookup ✅. Only "Authenticity
  verified: false" cases are `dblookup` of never-written addresses (see Gap 1).

**Mode actually exercised:** PULL, with connect **key-oblivious** — the device computes entry_key and
encrypts/decrypts; connect stores/serves opaque blobs by entry_key and holds no keys. The key-export /
PUSH-with-keys path is **dead code** (defined, never called). Encryption today buys **integrity**
(root commits over ciphertext) but **not host-confidentiality** (plaintext label co-stored — Gap 3).

---

## Gap 1 — DEGRADED: `wardVerify` (dblookup) non-membership is not device-proven  ⭐ correctness

**Symptom:** `dblookup` of an absent address returns `valid:false` ("Authenticity verified: false")
with `note:'non-membership (host-side only)'` — it reports host-DB absence *without* a device proof.
A malicious host could hide an existing label by claiming non-membership and the device would not
catch the omission (SUNDR-style). `dbdisplay` does NOT have this hole — it proves absence via the pull.

**Why:** a non-membership proof needs the **target** address's entry_key to pick the witness path.
The host cannot compute it (no K_index); only the device can (it sends it in `WARDProofRequest`). The
PUSH `WARDLookup` path can't supply it, so the branch was degraded.

**Fix (route non-membership through the PULL, reusing the working display path):**
- In `packages/connect/src/api/wardMethods/api/wardVerify.ts`, for the absent-entry case, drive the
  same device pull `wardDisplayAddress` uses: sync+adopt (already present) → a device op that emits
  `WARDProofRequest`, answered reactively by `buildAckByKey(blobRows(rows), req.entry_key)` → read the
  device's membership/non-membership verdict. Lowest-risk: reuse the `DisplayAddress`/`resolve_label`
  pull (device classifies) instead of pushing `WARDLookup`; membership may stay push (works) or unify
  on the pull.
- Expected result: absent-address `dblookup` → `valid:true, isMember:false` (proven absent).
- The stored entry_keys needed for the witness are already persisted (Gap 2) — no new storage.

Priority: **high** (only remaining correctness/security hole in the verified flows).

---

## Gap 2 — first-class `entry_key` column (IMPORTANT — matches design §2.1)

**Now:** `WardLeafBlob = {entryKey, entryType, nonce, tag, ct}` is persisted per entry, but nested in
the sqlite `blob` TEXT (JSON) column; `blobRows()` extracts it and serves proofs by walking all rows.
Correct and used (membership + non-membership witness), but not indexed/explicit.

**Why it matters:** `ward-design.md` §2.1 makes `entry_key` a **top-level Evolu-record field** (32 B
HMAC), not a nested attribute — it is the primary key of a WARD record and the trie path. The host
"knows `entry_key` but never `identifier`" (§3): the record should be **keyed by entry_key**, with the
identifier living only inside the encrypted `ct`. Storing it inside the blob JSON is a shortcut that
diverges from that shape and blocks a proper Evolu implementation (Gap 5) and reconstruction (Gap 10).

**Fix:**
- Promote `entry_key` to a first-class column in sqlite `addresses` (+ index) and to the
  `WardProvider` contract / Evolu record; populate from the device blob. O(1) `entryKey → row` lookup
  for `buildAckByKey` membership (currently O(n) `find`); makes "host indexes by entry_key" explicit.
- Longer-term (with Gap 3): make `entry_key` the actual primary key and move the identifier into `ct`,
  matching §2.1 exactly.

Priority: **high** (foundational shape for Gap 5 Evolu + Gap 10 reconstruction; user-flagged as
important).

---

## Gap 3 — POSTPONED DESIGN CHOICE: host-blindness not realized (plaintext co-stored)

**Now:** to keep Suite rendering labels directly, connect stores the **plaintext** label in the sqlite
`data` column *alongside* the encrypted `blob`, and sends plaintext `new_value` to the device in
`WARDQueueUpdate`. So the host DB is not blind — `ward-design.md` §0 ("host holds no keys / stores
only opaque blobs") is not achieved; encryption provides integrity, not secrecy-from-host.

**Fix (only if host-blindness is a goal) — exercise the currently-dead key-export/PUSH path:**
- Drop the plaintext `data` column (store only `blob`).
- Wire rendering (`wardDisplayAddress`, Suite label display, `dblookup` label return) through
  `WARDExportKeys`: connect calls `ward.export_keys(session, key_type)`, holds `K_index`/`K_data`
  **in memory only**, computes `entry_key` by identifier and decrypts `ct` to render.
- Resolve the two open questions first (see Gap 7): is `K_index` per-scope, and is export
  user-confirmed?

Priority: **deferred** (product decision). As-is is functional; this is the confidentiality upgrade.

---

## Gap 4 — BUILD: connect needs a clean rebuild in dependency order

**Symptom:** `@trezor/connect` tsc shows stale-type errors ("new field missing on OLD type") for the
ward files even though src is correct and runtime works (log shows the new wire fields).

**Cause:** project-reference `.d.ts`/`.tsbuildinfo` of dependencies are stale.

**Fix:** rebuild libs in order **@trezor/protobuf → @trezor/connect-common → @trezor/ward →
@trezor/connect** (protobuf/ward/connect-common libs already rebuilt this session). Then re-run the
emulator Suite flow. No code change; a full `yarn build` also does it.

Priority: **high but mechanical** (blocks a clean connect type-check/build only; runtime already fine).

---

## Gap 5 — MISSING: Evolu (suite-desktop) `WardProvider` implementation

Only the sqlite provider exists. suite-desktop needs an Evolu-backed `WardProvider` written against
the contract, storing the **encrypted blob keyed by entry_key** (and entry_key as a field per Gap 2).
It must persist `(entry_key, entry_type, nonce, tag, ct)` and, if Gap 3 is not taken, the plaintext
metadata for rendering.

Priority: **medium** (needed for the desktop app; CLI works on sqlite).

---

## Gap 6 — POSTPONED: firmware `key_type` / `device_id` not persisted per pending intent

**Now:** `service.intent`/`perform` default `key_type="address"`, `device_id=0` — they are **not**
framed into the `ward_store` pending record (`storage/ward_store.py` unchanged). So per-type / per-
device (§5 device-slot) writes aren't threaded end-to-end; only the default scope works.

**Fix:** extend the `ward_store` pending-record framing to carry `key_type` (length-framed) and
`device_id` (small int) alongside `app_id`, thread them through `queue_put`/`queue_get`/`_parse_body`/
`queue_set_computed` and their 8-tuple consumers (`perform`, `intent`, `discard`), and pass
`WARDQueueUpdate.key_type`/`device_id` (already on the wire) into `queue`.

Priority: **medium** (needed for the per-device-entry use case that motivated the whole change).

---

## Gap 7 — OPEN DESIGN QUESTIONS (gate Gap 3 / per-device privacy)

1. **`K_index` granularity:** single seed-wide (current) vs per-scope (derive per `app_id`/`key_type`/
   `device_id`). Per-scope is required for the PUSH export (Gap 3) to hand a host only the scopes it
   may compute/decrypt, and to keep per-device entries unguessable. `K_data` is already per-`key_type`.
2. **Key export user-confirmation:** should `WARDExportKeys` require an on-device confirm? (Firmware
   has `_confirm_export_keys` with a hold; tests would need to accept it or derive keys from the seed.)
3. **`device_id` semantics (§5.1):** user-chosen reclaimable slot (0..15) vs hardware/random. §5.1
   argues for the reclaimable slot (seed restore onto new hardware otherwise orphans records).

Priority: **decide before Gap 3 / Gap 6 hardening.**

---

## Gap 8 — ACCEPTED DIVERGENCES from `ward-design.md` (documented, not bugs)

- **`entry_type` in the clear** (needed to select per-type `K_data` before decrypt) — reverses §2.1's
  `leaf_type`-inside-ct, re-opening category partitioning / per-type edit-frequency leak. Accepted.
- **12-byte RFC-7539 nonce** instead of §2.1's 24-byte XChaCha20 (firmware primitive is RFC-7539);
  96-bit birthday bound per entry_type key, random-per-write mandatory (§4.5). `salt`→`nonce` renamed
  in `ward-design.md`.
- **Bitcoin `GetAddress` WARD label fields removed** — the shared message can't carry a required
  `repeated ward_proof`; label-on-address now lives only in `DisplayAddress`/`DisplayAddressWithProof`.
  `test_ward_get_address_label` is skipped as a result.
- **Internal-node encoding unchanged** — §2.2 skiplen/path-compression + §2.3 canonical-form
  invariants NOT adopted (leaf-only change). Device and host match on the current internal encoding.
- **`show.py` no warning on "unknown"** — a wrong/unverifiable proof shows the address titled
  "unknown" (already signals unverified; the host can't forge a false label). The broad
  `except → warning` is kept only for the label-*unavailable* path.

---

## Gap 9 — PRE-EXISTING firmware TODOs (not introduced here, tracked for completeness)

- **gaps.md #1 (cold-start):** first `perform` can proceed without a prior attested/reconciled round
  in-session; leans on WM co-sign + server CAS. Harden by requiring an attested round.
- **gaps.md #2/#3:** the WM signs the host-supplied `(counter, mac)`; validate `(WM_HEAD, DB_HEAD)`
  consistency host-side before adopt instead of relying on firmware to reject late at reconcile.
- **connect-cli offline path** (`useDevice=false`): now a blob-root consistency check only — it cannot
  compute leaves without the device (no keys). Effectively device-only for real writes/verifies.

---

## Gap 10 — MISSING: per-batch root lineage (`parent_hash`/`target_hash` + root MAC) for MPT reconstruction  ⭐ design-core

**Now:** nothing stores the root a write transitions **from** or **to**, nor the per-transition root
MAC / CAS signature. sqlite has `addresses` (current rows) + a single `tree_state` (current
root/counter/mac). "Reconstruction" = rebuild the root from **all current rows**
(`computeRootFromBlobs(getAllEntries)`). That works only for a single always-online host that holds
the full current state; it is **not** the design's model.

**What the design requires (§2.1 / §2.4 / §7):**
- Each Evolu record carries `parent_hash` (root this batch transitions **from**) and `target_hash`
  (root this batch transitions **to**). These are unauthenticated hydration hints (§2.4).
- Hydration (§7) = **backward walk** from the WARD head: select records with `target_hash = root_head`,
  read their `parent_hash`, repeat to a baseline/snapshot; then **forward replay**; then a
  **per-batch root check** — recompute the root after applying batch B and require it to equal
  `B.target_hash` (this, not the links, is what proves a batch genuine). Orphan / failed-CAS batches
  are never visited and thus ignored for free.
- The **authenticated** lineage is the **CAS-signature chain** (§2.4): each signs
  `root_prev ‖ root_new ‖ C_new ‖ t_anchor` under `K_sig`; `root_new` of one = `root_prev` of the
  next, counters increment by one. The per-transition **root MAC** (`HMAC(mac_key, wallet_id ‖ counter
  ‖ root)`, already returned by the device at confirm) binds each root to its counter. Needed for
  §3.1 fast-forward and §8.2 one-step constrained rollback (both require prev/target roots + counter +
  signature).

**Fix (implementation plan):**
1. **Store the transition per committed write/batch.** Add a `transitions` (a.k.a. `batches`) table
   keyed by `(ward_id, counter)` with columns: `prev_root` (parent_hash), `target_root`
   (target_hash), `target_root_mac`, and optionally the WM final `wm_signature` / `t_anchor`. Populate
   from the device round: `perform` yields `counter_T`/`root_T`; `confirmed_by_wm` yields the installed
   `counter`/`new_root`/`root_mac`; the WM final signature is in hand at confirm. Persist
   `(counter, prev_root=<root before>, target_root=new_root, target_root_mac=root_mac[, wm_signature])`.
   Also stamp each `addresses` row with the `counter` (== C_leaf, already inside `ct`) that produced it
   so an entry links to its batch.
2. **Store `parent_hash`/`target_hash` on the record too** (design §2.1 shape) for the Evolu provider,
   so a fresh Suite can do the backward walk from the relay's record set without a side table.
3. **Implement §7 hydration** in `@trezor/ward`: `hydrate(records)` = backward walk
   `target_root → prev_root` from the head, forward replay of each batch's leaf blobs (keyed by
   entry_key — needs Gap 2), and a **per-batch root check** (`computeRootFromBlobs(state_after_B) ===
   B.target_root`), rejecting a batch whose replay root ≠ its `target_root` (§8.1 case 3/5 → rollback).
4. **Verify lineage authenticity**: check each `target_root_mac` against its counter, and (where the
   CAS/WM signature is stored) that the signature chain is contiguous (`root_new`→`root_prev`, counters
   +1). This is the precondition for §3.1 fast-forward and §8.2 rollback, neither of which is
   implemented today.
5. **Snapshots (§7)**: a self-verifying full leaf-set dump at counter X (root over it == attested
   `root_X`) so a fresh host doesn't replay from genesis. Optional but recommended once the batch DAG
   exists.

**Depends on:** Gap 2 (entry_key-keyed records) — reconstruction replays leaf blobs keyed by entry_key.

Priority: **high** (this is the actual design hydration/verification model; the current
"rebuild-from-all-current-rows" only holds for one always-online host and gives no per-batch/lineage
verification, no fast-forward, no rollback).

## Suggested order

1. Gap 4 (rebuild) — unblocks a clean connect build/type-check.
2. Gap 1 (wardVerify non-membership pull) — closes the last correctness hole in the working flows.
3. **Gap 2 (first-class entry_key column)** — foundational record shape; prerequisite for 4 and 5.
4. **Gap 10 (per-batch lineage + §7 hydration/verification)** — the real reconstruction model
   (parent_hash/target_hash + target_root_mac + per-batch root check); also unlocks §3.1 fast-forward
   and §8.2 rollback. Depends on Gap 2.
5. Gap 7 decisions → Gap 6 (per-type/device store framing) — enables the per-device use case.
6. Gap 5 (Evolu provider, built on the Gap 2 + Gap 10 record shape) — desktop.
7. Gap 3 (host-blind via key export) — confidentiality upgrade, if desired.

---

# Execution plan (selected: Gaps 2, 10, 1, 6)

Actionable plan for the four gaps chosen for the next implementation phase. **Order matters:** Gap 2
is a prerequisite for Gap 10; Gap 1 and Gap 6 are independent. Not yet implemented.

**Shaping facts (confirmed in code):**
- Connect is pull / key-oblivious: device computes `entry_key` + encrypts/decrypts; connect stores
  opaque `(nonce,tag,ct)` blobs and answers `WARDProofRequest` via `buildAckByKey`
  (`packages/connect/src/api/wardMethods/proofAck.ts`).
- Host already holds prev/target roots per write: `loadHead` → pre-write `TreeState.root` (parent_hash);
  `confirmed_by_wm` → `new_root` (target_hash) + `root_mac` + `counter`. **Gap 10 needs no firmware
  change.**
- Firmware pending-record framing (`core/src/storage/ward_store.py`): `pid+wid+counter+state+root+mac
  +LV(address)+LV(old)+LV(new)+LV(app_id)`. Gap 6 appends `LV(key_type)+device_id`, backward-compatible
  past-end reads (as `app_id` was added).

## Gap 2 — first-class `entry_key` column (host TS) [do first]
- `packages/ward/src/types/index.ts`: add top-level `entryKey: string` to `WardRow` (keep
  `WardEntry.blob` = nonce/tag/ct/entryType).
- `storage/sqlite/index.ts`: `entry_key TEXT` column + index; populate from the device blob on `upsert`;
  return in `lookup`/`getAllEntries`; add `getByEntryKey(wardId, entryKey)`. Mirror in in-memory
  provider + `WardProvider` contract.
- `proof`/`app`: `blobRows()` reads the top-level `entryKey`; `buildAckByKey` membership uses indexed
  `getByEntryKey` (O(1)) instead of O(n) `find`. Reuse `commitOf`/`proofByKey`/`nonMembershipByKey`.

## Gap 10 — per-batch root lineage + §7 hydration (host TS) [needs Gap 2]
- Storage (`storage/sqlite` + contract + in-memory): `transitions` table keyed `(ward_id, counter)`:
  `prev_root`, `target_root`, `target_root_mac` (+ optional `wm_signature`, `t_anchor`); methods
  `putTransition`/`getTransitions`. Stamp each `addresses` row with its `counter` (== C_leaf); persist
  `parent_hash`/`target_hash` on the record shape (§2.1).
- Populate (`api/wardUpdate.ts`): after `session.confirm`, `putTransition(wardId, {counter:
  installed.counter, prevRoot: tree?.root ?? '', targetRoot: installed.root, targetRootMac:
  installed.rootMac})` — all host-side already.
- `hydrate(records, transitions, headRoot)` in `packages/ward/src/app`: backward walk
  `target_root→prev_root` from head; forward replay of each batch's leaf blobs by `entry_key`;
  per-batch root check `computeRootFromBlobs(state_after_B) === B.target_root` (mismatch ⇒ reject,
  §8.1 case 3/5); verify each `target_root_mac` vs counter (+ CAS/WM sig contiguity if stored); ignore
  orphan batches. Wire into `loadHead`/new `resolveHead`. Unblocks §3.1 fast-forward & §8.2 rollback.

## Gap 1 — `wardVerify` non-membership via pull (host TS) [independent]
- `api/wardVerify.ts`: for the absent-entry branch, stop returning `valid:false`; drive the device pull
  `wardDisplayAddress` uses (sync+adopt → `WARDProofRequest` answered by `buildAckByKey(blobRows(rows),
  req.entry_key)` → read the device's classification). Lowest-risk: reuse the `DisplayAddress`/
  `resolve_label` pull; membership may stay push or unify. Result: absent `dblookup` →
  `valid:true, isMember:false` (proven absent).

## Gap 6 — firmware `key_type`/`device_id` framing (firmware Python) [independent]
- `core/src/storage/ward_store.py`: append `LV(key_type)+device_id(1B)` after `app_id` in `_build_body`;
  read in `_parse_body` (→10-tuple, past-end defaults `"address"`/0); update `queue_put`,
  `queue_set_computed`, and all 8-tuple consumers (`perform`/`intent`/`discard`).
- `apps/ward/service.py`: `queue` stores them; `intent`/`perform` read + pass to `entry_key(k_index,
  app_id, address, key_type, device_id)` (replacing defaults). `apps/common/ward.py queue` +
  `apps/ward/queue.py` pass `msg.key_type`/`msg.device_id` through (already on `WARDQueueUpdate`;
  trezorlib threads them — no proto change). `device_id` = user-chosen slot (§5.1); slot-capture UX
  deferred (Gap 7).

## Verification
- Gap 2: `@trezor/ward` jest (`getByEntryKey` hit; membership indexed) + `type-check`.
- Gap 10: jest — N fixture batches + transitions; `hydrate` reproduces head root, passes per-batch
  checks; tampered target_root / omitted batch rejected; orphan ignored. Emulator: several `dbchange`,
  then fresh-host hydrate matches device root.
- Gap 1: emulator `dblookup` of absent address → `valid:true/isMember:false`; false non-membership
  caught on-device.
- Gap 6: emulator `dbchange` with non-default `key_type`/`device_id` → distinct `entry_key` path; slots
  don't collide; default-scope `pytest tests/device_tests/misc/test_ward*.py` still green.
- Connect prerequisite: rebuild **@trezor/protobuf → connect-common → @trezor/ward → @trezor/connect**.
