# Encrypted entries — implementation plan (confidentiality completion)

Entry-point plan for finishing the `ToDo-encrypted_entries` work. It builds on the docs in this
directory:

- `TODO_Entry_key_as_MAC.md` — the keyed-path + encrypted-leaf design and what is already implemented.
- `scaffolding_encryption.md` — the current encrypted model (§1–§6) + the §11 privacy analysis
  (privacy-relevant vs privacy-violating wire fields). `scaffolding_no_encrypt.md` is the stale
  plaintext baseline (broad lifecycle/WM flow only).
- `planned_fixes.md` — Gaps 1–10, **with execution plans already written for Gaps 2, 10, 1, 6**.

**What is already implemented** (do not re-plan): keyed `entry_key = HMAC(K_index, scope‖identifier)`,
per-type `K_data`, ChaCha20-Poly1305 leaf encryption, pull proofs served by opaque `entry_key`,
device-produced blobs persisted by the host, WM freshness/finalization. Device tests green.

**What this plan adds** (the part the "encrypted entries" name is really about — not yet planned as
execution steps): realize the design §0 property — *host holds no keys and stores only opaque blobs* —
while Suite can still render labels. Concretely: safe per-scope keys, key-export wiring, host-blind
storage, the wire-plaintext posture from §11, and the Evolu provider. Gaps 3, 5, 7 + the §11 audit.

---

## 0. Prerequisites

- **Gap 2 — DONE (2026-08-04, verified).** `entry_key` promoted to a first-class, indexed host record
  field: sqlite `entry_key` column (+ `addresses_entry_key` index, ALTER migration) populated from the
  device blob; `getByEntryKey(wardId, entryKey)` on the `WardProvider` contract + in-memory + sqlite;
  `WardRow.entryKey` top-level. `@trezor/ward` tsc clean, 21 jest tests pass.
- **Gap 1 — RESEQUENCED (see below).** Route `wardVerify` non-membership through a device-verified
  proof so reads carry no plaintext identifier / can't be spoofed by omission.

**Sequencing insight (found during Gap 2):** Gap 1's non-membership is *not* a pure connect-TS change
as `planned_fixes.md` assumed. A non-membership proof needs the **target** `entry_key`, which the host
can only obtain by either (a) the device computing it and pulling (needs a firmware silent pull-verify
op — `DisplayAddress` pulls but shows a screen), or (b) the host computing it from an **exported
`K_index`** and pushing the witness via `WARDLookup`. Option (b) falls out **for free once E2 (key
export) exists** and needs no firmware change. **Therefore do Gap 1 AFTER E1+E2**, not before. Revised
order: `Gap 2 (done) → E1 → E2 → Gap 1 → E3 → E4 → Gap 10 → E5`.

---

## 1. Design decisions to lock (Gap 7)

- **D1 — `K_index` becomes per-scope.** Today `_derive_k_index()` is seed-wide, so exporting it would
  let the host compute the `entry_key` of **every** scope (all apps, key_types, device slots),
  defeating the per-device unlinkability that motivated the migration. Change to
  `K_index(app_id, key_type) = SLIP21(seed, ["ward","K_index", app_id, key_type])`; the `entry_key`
  preimage moves `app_id`/`key_type` from the HMAC **message** into the **key derivation**, leaving
  `entry_key = HMAC(K_index(app_id,key_type), device_id ‖ identifier)`. **Recommended** — it is the
  precondition for a safe per-type export. Cost: it changes the frozen `entry_key` byte layout, so
  firmware + `ward_crypto.py` + test vectors must change together (see Phase E1).
- **D2 — `WARDExportKeys` gating.** Keep the on-device hold-confirm (`_confirm_export_keys`), return the
  **scoped** `(K_index(app_id,key_type), K_data(key_type))`, host holds them **in memory only**
  (session-scoped, never persisted). Add `app_id` to the export request.
- **D3 — `device_id` = user-chosen reclaimable slot (§5.1).** This plan wires the crypto/export; the
  setup-time slot capture/confirm UX is deferred (tracked by Gap 6).

---

## 2. Phases

### Phase E1 — per-scope key derivation (D1)  [firmware + trezorlib]
- `core/src/apps/ward/service.py`: `_derive_k_index(app_id, key_type)`; fold `app_id`/`key_type` into
  the SLIP-21 path; `entry_key()` takes the already-scoped key and only mixes `device_id ‖ identifier`.
  Thread the (app_id, key_type) through `entry_key_for`/`lookup`/`lookup_label`/`perform`/`intent`.
- `python/src/trezorlib/ward_crypto.py`: mirror exactly; **re-freeze** the vectors in
  `python/tests/test_ward_crypto.py` (they pin the canonical layout).
- `common/protob/messages-ward.proto`: add `app_id` to `WARDExportKeys`/`WARDExportKeysAck`; regen all
  three binding sets.
- Verify export(type A) cannot compute type B / other-scope paths.

### Phase E2 — key-export wiring on the host  [connect + @trezor/ward]
- `@trezor/ward`: add host-side `entryKeyFor(kIndex, scope, identifier)` and `decryptLeaf(kData, …)`
  (mirror `ward_crypto`) so a key-holding host can compute `entry_key` by identifier and decrypt `ct`.
- connect: a session-scoped **in-memory** `WardKeyStore` that calls `ward.export_keys(session, appId,
  keyType)` once per rendered `(appId, keyType)` and caches `(kIndex, kData)`; never persisted, cleared
  on session end. (Firmware `export_keys` + trezorlib wrapper already exist.)

### Phase E3 — host-blind storage (Gap 3 / scaffolding §6-C)  [@trezor/ward storage + connect]
- **Drop the plaintext `data` column.** Store **only** the encrypted blob keyed by `entry_key`
  (`entry_type, nonce, tag, ct, counter` + the Gap 10 lineage). Applies to sqlite and the Evolu
  provider (Phase E5).
- **Rendering** (`wardDisplayAddress` label, `wardVerify`/dblookup label return, Suite label list):
  decrypt the stored `ct` with the in-memory exported `K_data` from E2 — no plaintext at rest.
- `wardUpdate`: still receives plaintext metadata from the caller (it is the writer) and sends it to
  the device for the trusted confirm + device-side encryption, but `commitLocal` now persists **only
  the blob** — never the plaintext.
- `WardProvider` contract: `lookup` returns a decrypted entry only when keys are loaded (else the
  opaque blob); `getAllEntries` returns blobs.

### Phase E4 — wire-plaintext posture (scaffolding §11)  [audit + close]
- **Reads:** fully pull-by-`entry_key` after Gap 1 (+ display already). No plaintext identifier on the
  read wire. Deprecate/remove the plaintext-address PUSH `WARDLookup` verify path (superseded by the
  pull).
- **Writes:** `WARDQueueUpdate` keeps plaintext `identifier`/`value`/`app_id` — **required** for the
  on-device trusted confirm (device shows Domain/Key/Value) and for device-side encryption. This is
  device-ward from the writing host (which already knows what it writes), not a new at-rest/relay leak.
  Document as an accepted, inherent exposure; the confidentiality target (at-rest cache + relay +
  reads) is closed by E3 + Gap 1.
- **`WARDExportKeys`:** the deliberate §0 downgrade — gated (D2), per-scope (D1), in-memory only.

### Phase E5 — Evolu provider (Gap 5)  [suite-desktop]
- Implement `WardProvider` against Evolu, records **keyed by `entry_key`**, storing only
  `(entry_type, nonce, tag, ct, counter, prev_root/target_root)` — **no plaintext**. Rendering via the
  E2 exported keys. Reuse the Gap 10 lineage/reconstruction path.

---

## 3. Order & dependencies

```
Gap 2 (DONE) ─▶ E1 (per-scope keys) ─▶ E2 (export wiring) ─▶ Gap 1 (non-membership) ─▶ E3 (host-blind) ─▶ E4 (wire audit)
                                                                                  └─▶ Gap 10 (lineage) ─▶ E5 (Evolu)
```
Firmware/host stay layout-locked: any `entry_key`/leaf change (E1) lands in firmware + `ward_crypto` +
frozen vectors together, then connect rebuilds in order **@trezor/protobuf → connect-common →
@trezor/ward → @trezor/connect**.

## 4. Verification
- **E1:** re-frozen `ward_crypto` vectors; firmware ↔ trezorlib ↔ reference `entry_key` match for a
  scoped case; a CPython test that keys for `(bitcoin,address)` cannot derive the path/decrypt for
  `(bitcoin,label)` or another `device_id`.
- **E2/E3 (emulator):** after `dbchange`, the host DB holds **no plaintext** (blob-only, `data` column
  gone); `dbdisplay`/`dblookup` still render the label by decrypting with exported keys; a host
  **without** exported keys can still serve proofs by `entry_key` but cannot render plaintext.
- **E4:** wire audit — reads carry only `entry_key` (no plaintext identifier); `WARDExportKeys` prompts
  an on-device confirm; the plaintext PUSH `WARDLookup` path is gone.
- **E5:** Evolu provider round-trips blob-only records + reconstructs via lineage; matches the device root.
- **Regression:** `pytest tests/device_tests/misc/test_ward*.py` green; connect jest green after rebuild.

## 5. Explicit non-goals / accepted exposures (from scaffolding §5 / §11)
- `entry_type` and ciphertext length-bucket remain visible to the host/relay (needed to pick `K_data`
  and for proof serving) — accepted §2.1 divergence.
- Plaintext identifier/value on `WARDQueueUpdate` (writer-side, for the trusted confirm) — inherent.
- `entry_key` is a path PRF, **not** the write-authorization mechanism (that stays on-device confirm +
  ACL/domain binding + WM signature).
