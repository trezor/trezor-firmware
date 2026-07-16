# Firmware Merkle-tree signing scheme

Status: **design + partial prototype** (T3W1/STM32U5, `pq_secure_boot` feature).
This document is the authoritative schema — the on-flash / on-wire contract that
the boardloader, bootloader, firmware, host tooling and cross-validation all
agree on. Sections are marked **[impl]** (built today), **[proto]** (host-only
prototype) or **[design]** (agreed, not built).

## 1. Overview

The founder signs **one** Merkle root — `modelRoot` — that spans **all models,
all firmware variants, all bootloaders** (and, transitively, apps and
translations). There is exactly one signature.

Verification is split across three trust domains, each recomputing only the part
of the tree it owns and bridging to the root it inherits via a Merkle path:

| Domain | computes | folds via | up to | trust |
| --- | --- | --- | --- | --- |
| **boardloader** | `H(bootloader)` + model leaf | model path (`boot_header_merkle_proof`) | `modelRoot` | verifies the **signature** |
| **bootloader** | `H(firmware manifest)` | firmware path (`firmware_proof`) | `firmwareRoot` | trusts it (in the boardloader-verified boot header) |
| **kernel** (opt) | `H(app)` | app path | `appRoot` | trusts it (in the bootloader-verified manifest) |

`firmwareRoot` and `appRoot` are ordinary **internal nodes** of the single tree,
but they are also **materialized as fields** in their parent node (checkpoints),
so a lower domain can verify its subtree locally against a root it already trusts
without re-walking to `modelRoot` or re-checking the signature.

The founder's build system produces `modelRoot`; the founder compares it against
the value shown on their Trezor, and the Trezor can show what changed since last
time (e.g. a new bootloader vs. just a new Solana app).

## 2. Tree shape

```
modelRoot                                            [signed]
├── modelIntNode…
│   └── model leaf  { hwModel, version, fixVersion, …,
│                     firmwareRoot, bootloaderHash }      ← boot header (TRZQ)
│         └── firmwareRoot                                (materialized field)
│               ├── variant manifest (universal)  { firmwareType, appRoot,
│               │        translationsRoot, hashDirectory[secmon,kernel,core] }
│               │     └── appRoot                          (materialized field)
│               │           └── app leaves (btc, eth, solana, …)
│               ├── variant manifest (bitcoin-only)
│               ├── variant manifest (prodtest)
│               └── nrf            (shared, variant-agnostic — see §7)
└── … other models
```

## 3. Hashing primitives  **[impl]**

Matches `trezorlib.merkle_tree` and `boot_header_merkle.h` byte-for-byte:

- **Leaf:** `leaf(x) = SHA256(0x00 || x)`
- **Internal:** `node(a,b) = SHA256(0x01 || min(a,b) || max(a,b))`
- **Subtree build:** sort leaves by hash, pair left→right, carry an odd node up
  (only the bottom level is sorted).
- **Proof fold:** `for sibling in proof: node = node(current, sibling)` — a
  sequential sorted-pair fold (a standard Merkle authentication path).

The `0x00`/`0x01` prefixes give domain separation (a proof for an internal node
can't be replayed as a leaf, and vice-versa).

## 4. Model layer (boardloader)

### 4.1 Model leaf = the boot header (TRZQ)  **[impl]**

The model leaf is the existing `boot_header_auth_t` hashed with the bootloader
code: `leaf = SHA256(0x00 || auth_bytes[auth_size] || SHA256(bootloader_code))`
(see `boot_header_calc_merkle_root`). Relevant authenticated fields:

| field | meaning |
| --- | --- |
| `magic` = `TRZQ` | boot header |
| `hw_model`, `hw_revision` | model identity |
| `version`, `fix_version`, `min_prev_version`, `monotonic_version` | versioning / downgrade |
| `header_size`, `auth_size`, `code_size` | layout (self-describing) |
| **`firmware_root`** (32) | checkpoint: root of this model's firmware tree |

`bootloaderHash` in the diagram = `SHA256(bootloader_code)`, folded into the leaf.

### 4.2 Model path = `boot_header_merkle_proof_t`  **[impl]**

Co-path from the model leaf up to `modelRoot`, stored right after the auth part.
`node_count = 0` today (single model per signed root); non-empty once the founder
batches multiple models under one `modelRoot`. The boardloader folds it and
verifies the founder signature over `modelRoot`.

## 5. Firmware layer (bootloader)

### 5.1 Variant manifest ("firmware directory")  **[proto host]**

The variant leaf is a **manifest** placed at the **start of the firmware image**,
before the module headers. It keeps the TRZM module headers (§5.3): each entry
references its module by `header_hash`, which commits the module's `code_hash`
(a single SHA-256 over the whole module code).

Byte layout (little-endian), variant leaf = `SHA256(0x00 || manifest)`:

| offset | field | type | notes |
| --- | --- | --- | --- |
| 0 | `magic` = `TRZD` | u32 | firmware directory |
| 4 | `firmware_variant` | u32 | `fw_variant_t` (== `vendor_fw_type_t`); authenticated |
| 8 | `app_root` | 32 | root of the app tree; **zero** until apps exist |
| 40 | `translations_root` | 32 | root of translations; **zero** until they exist |
| 72 | `module_count` | u32 | |
| 76 | `entry[module_count]` | — | 48 bytes each |

Entry:

| offset | field | type | notes |
| --- | --- | --- | --- |
| 0 | `module_type` | u32 | role: secmon / kernel / core (`fw_module_type_t`) |
| 4 | `flags` | u32 | reserved (0) |
| 8 | `addr` | u32 | module location (offset from firmware region start) |
| 12 | `size` | u32 | module code size |
| 16 | `header_hash` | 32 | `SHA256(TRZM header)` — commits `code_hash` |

Fixed part 76 B + 48 B/entry. `firmware_variant` is taken from the
kernel+coreapp module. The module set/count/roles are **authenticated data** —
the bootloader iterates the directory rather than hardcoding a role table, so
adding/splitting modules of known types needs no bootloader code change (only a
re-sign). New module *types* or new boot-flow relationships still need code.

### 5.2 Firmware path = `firmware_proof`  **[impl 11b]**

Co-path from the variant leaf up to `firmwareRoot`. Stored **unauthenticated** in
the boot header (`boot_header_unauth_t.firmware_proof_count` +
`firmware_proof_nodes[BOOT_HEADER_FW_PROOF_MAX_NODES=4]`); verified by
recomputation against the (signed) `firmware_root`, so unauth is safe. Written at
install time (OTA phase 1 / factory), like `firmware_type`. `count = 0` ⇒
single-variant (`variant leaf == firmwareRoot`, identity fold) — backward
compatible. This is the *middle* segment of the one tree; `boot_header_merkle_
proof` is the *top* segment.

### 5.3 Module header (TRZM)  **[impl]**

`firmware_module_header_t` (fixed 52 B): `magic=TRZM, hw_model, module_type,
version[4], code_size, code_hash[32]`. Reserved 0x400 header region precedes the
code. `code_hash = SHA256(whole module code)` — a single hash, **not** per-chunk;
the manifest's `header_hash` commits the whole header incl. `code_hash`, and boot
/ install verify code integrity via `firmware_module_verify_code` (one
module-sized hash). The image is written in full before boot, so there is no
sub-module/per-chunk streaming verification; install rejects at module
granularity (per §"incremental verify") and the whole-tree check is the backstop.
If in-flight per-transport-chunk verify is ever required, the right shape is a
variant-A hash chain in place of the single `code_hash` (same 32 bytes), not the
old per-chunk array.

### 5.4 Firmware image layout  **[design]**

```
firmware.bin:
  [ manifest ]                          offset 0 (reserved region at firmware start)
  [ secmon:  TRZM header (0x400) | code ]
  [ kernel:  TRZM header (0x400) | code ]
  [ core:    TRZM header (0x400) | code ]   (kernel/core split is future)
```

The manifest sits at the firmware start; each entry's `addr` is the authenticated
offset of its module. (Reserved manifest region size / alignment: TBD — must fit
the largest manifest and align the first module to the flash/chunk boundary.)

## 6. App layer (kernel) — **[design]**

`appRoot` (a field in the variant manifest) is the root of a Merkle tree of
installable apps (btc, eth, solana, …). A module such as the kernel verifies an
app it loads by folding the app's Merkle path up to `appRoot` (which it trusts
because the manifest is bootloader-verified). `translations_root` is analogous
for translation blobs. Neither is built yet; the manifest reserves zeroed fields
for them.

## 7. nRF placement — **[design]**

The nRF (BLE co-processor) firmware is **variant-agnostic and model-specific**, so
it is a **shared node at the `firmwareRoot` level**, NOT an entry duplicated in
each variant manifest. Two options:

1. **(preferred)** a sibling leaf/subtree under `firmwareRoot`, alongside the
   variant manifests — bootloader-verified, reuses `firmwareRoot`.
2. a separate `nrfRoot` peer of `firmwareRoot` in the model leaf —
   boardloader-verified.

Choice hinges on which layer installs/verifies the nRF (bootloader ⇒ option 1).
T3W1 keeps its nRF **embedded** in kernel+coreapp (`.nrf_app`) for now (covered
transitively); the shared-sibling split is for future flash-constrained models,
and needs a phase-2 transfer-to-nRF-chip install step.

## 8. Storage summary

| item | where | authenticated? |
| --- | --- | --- |
| `modelRoot` signature | boot header unauth (`slh`/`ec` sigs) | is the signature |
| `firmware_root` | boot header **auth** | yes (in model leaf) |
| model path (`boot_header_merkle_proof`) | boot header, after auth | folded into signed root |
| `firmware_type` | boot header **unauth** | no (device-written) |
| firmware path (`firmware_proof`) | boot header **unauth** | no (verified by recompute) |
| variant manifest | **firmware image start** | yes (leaf under `firmwareRoot`) |
| TRZM headers + chunk hashes | per module, in firmware image | yes (via manifest `header_hash`) |

## 9. Verification flow

**Boot (boardloader → bootloader → firmware):**
1. Boardloader: recompute model leaf from the boot header + `H(bootloader_code)`,
   fold `boot_header_merkle_proof` → `modelRoot`, verify signature. Jump to
   bootloader.
2. Bootloader: read the manifest at firmware start, `variant_leaf =
   SHA256(0x00 || manifest)`, fold `firmware_proof` → compare to `firmware_root`
   from its (boardloader-verified) boot header. Then for each manifest entry:
   `SHA256(TRZM header @ addr) == header_hash`, and verify code chunks vs
   `header.chunk_hashes`. Jump to the entry module (secmon).
3. Kernel (opt): to load an app, fold the app's path → `appRoot` from the
   (bootloader-verified) manifest.

## 10. Implementation status

- **[impl]** hashing primitives + fold; `boot_header_calc_firmware_root` (subtree
  build + proof fold); `firmware_verify` / `firmware_verify_headers`;
  cross-validation harness (`tests/fw_merkle`).
- **[impl]** `firmware_proof_nodes` in `boot_header_unauth_t` +
  `fw_check_pq.c` reads and folds it (11b); Python `BootHeaderUnauth` mirrors.
- **[impl]** build-time variant stamping (universal=2 / btc-only=3).
- **[proto host]** founder tree over variants + per-variant proofs
  (`firmware_module.build_founder_tree`); manifest build (`build_manifest` /
  `variant_manifest` / `variant_leaf`) — variant leaf = `H(0x00 || manifest)`.
- **[design / TODO]** switch the shared verify math from the module *subtree* to
  the *manifest* leaf; store the manifest at firmware start; model tree →
  `modelRoot` (multi-model, non-empty `boot_header_merkle_proof`); app tree +
  `appRoot`; translations; nRF as a shared node; kernel/core split; production
  signing + custom/delegated (non-founder) path.

## 11. Open questions

- Manifest reserved-region size + module alignment at firmware start.
- nRF: option 1 vs 2; is it ever genuinely per-variant?
- `firmware_type` in the manifest = variant marker only (authenticated), with the
  custom/official bit still *derived* from the verification tier — confirm.
- Whether `boot_header_merkle_proof` (model tree) is ever populated (batched
  multi-model signing) or stays single-leaf.
- Kernel vs coreapp as separate modules (boot-flow change).
