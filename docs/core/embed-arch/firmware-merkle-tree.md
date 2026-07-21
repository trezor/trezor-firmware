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
| **kernel** (opt) | `H(app)` | app path | a future app root | would be added to the manifest when apps exist (§6) |

`firmwareRoot` is an ordinary **internal node** of the single tree,
but it is also **materialized as a field** in its parent node (a checkpoint),
so a lower domain can verify its subtree locally against a root it already trusts
without re-walking to `modelRoot` or re-checking the signature. A future app root
(§6) would be materialized the same way, in the variant manifest.

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
│               ├── variant manifest (universal)  { firmwareType,
│               │        translationsRoot, hashDirectory[secmon,kernel,core] }
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
before the modules. Each entry commits its module's code **directly** via
`code_hash` (a single SHA-256 over the whole module code) — there is no separate
per-module header, so the commitment is a single hop (variant leaf → manifest →
`code_hash` → code).

Byte layout (little-endian), variant leaf = `SHA256(0x00 || manifest)`:

| offset | field | type | notes |
| --- | --- | --- | --- |
| 0 | `magic` = `TRZD` | u32 | firmware directory |
| 4 | `firmware_variant` | u32 | `fw_variant_t` (== `vendor_fw_type_t`); authenticated |
| 8 | `firmware_version` | 4×u8 | major, minor, patch, build (kernel+coreapp) |
| 12 | `translations_root` | 32 | root of translations; **zero** until they exist |
| 44 | `module_count` | u32 | |
| 48 | `entry[module_count]` | — | 48 bytes each |

Entry:

| offset | field | type | notes |
| --- | --- | --- | --- |
| 0 | `module_type` | u32 | role: secmon / kernel / core (`fw_module_type_t`) |
| 4 | `flags` | u32 | `FW_MANIFEST_ENTRY_FLAG_*` (e.g. `_FLAG_BOOT`) |
| 8 | `addr` | u32 | module **code** offset from firmware region start |
| 12 | `size` | u32 | module code size |
| 16 | `code_hash` | 32 | `SHA256(whole module code)` |

Fixed part 80 B + 48 B/entry. The module set/count/roles are **authenticated data** —
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

### 5.3 Module code commitment  **[impl]**

There is **no per-module header**. Each manifest entry commits its module's code
directly: `code_hash = SHA256(whole module code)` over `size` bytes at `addr`.
Boot / install verify integrity by rehashing the code and comparing to the
(authenticated) `code_hash` — one module-sized hash. The image is written in full
before boot, so there is no sub-module/per-chunk streaming verification; install
rejects at module granularity (per §"incremental verify") and the whole-tree
check is the backstop. The entry's `addr`/`size` are emitted by the linker
(`manifest_header.S` from linker symbols); `code_hash` is filled post-build
(`headertool_pq`) over the placed code.

### 5.4 Firmware image layout  **[impl]**

```
firmware.bin:
  [ manifest ]              offset 0 (reserved region FW_MANIFEST_REGION = 0x400)
  [ secmon:  code ]         (aligned to CODE_ALIGNMENT)
  [ kernel:  code ]         (aligned to CODE_ALIGNMENT; kernel/core split is future)
```

The manifest sits at the firmware start (reserved `FW_MANIFEST_REGION` = 0x400);
each entry's `addr` is the authenticated offset of its module **code** (no header
region), aligned to `CODE_ALIGNMENT`.

### 5.5 Custom (unofficial) firmware = `FW_VARIANT_CUSTOM`  **[impl]**

Custom firmware is a **first-class tree variant** (`FW_VARIANT_CUSTOM = 1`), not
a flag. The founder signs one custom slot into `firmwareRoot` whose variant leaf
is computed with **everything the creator controls zeroed** — the manifest
`firmware_version` and the kernel+coreapp (`FW_MODULE_APP`) entry's `size` +
`code_hash`. The app entry's `module_type`/`flags`/`addr` and the **entire secmon
entry** stay real, so the founder still binds the secmon and the app's role +
placement. Because size/version/code_hash are all zeroed, ONE founder-signed slot
accepts **any** creator app (any code, size, version); the creator ships their
real values on flash (used for integrity + display only).

The manifest then serves **two roles**, and the zero-for-fold substitution is
centralized in one place (`boot_header_variant_leaf`, mirrored in the Python
`authenticity_manifest`):
- **Authenticity** (founder): recompute the variant leaf with the app `code_hash`
  treated as zero → fold → must equal `firmwareRoot`. Proves the secmon +
  structure are founder-authorized and this is the sanctioned custom slot. Any
  creator app authenticates to the same leaf, so the app is **founder-UNbound**.
- **Integrity** (creator): the app code must hash to the on-flash (creator)
  `code_hash`. Corruption/attestation only — NOT app authenticity.

Security posture: the secmon stays founder-signed (bound even for custom); custom
runs **unprivileged** (no secret/provisioning access, boot warning), is
storage-isolated (`firmware_type` == the variant, so custom is its own domain;
custom↔custom is shared), and installs **only on an unlocked bootloader**.
`firmware_type_is_official()` is a positive allow-list (fails toward restricted);
`is_custom` / privilege gates never grant official on a glitched byte. The
build-time `--unsafe-fw` selects `FW_VARIANT_CUSTOM`; the app is still filled with
its real `code_hash` (the signer zeroes it only for the leaf).

## 6. App layer (kernel) — **[design]**

A future app root would be the root of a Merkle tree of installable apps (btc,
eth, solana, …). A module such as the kernel would verify an app it loads by
folding the app's Merkle path up to that root (which it trusts because the
manifest is bootloader-verified). When apps are built, the app root would be
added to the variant manifest, materialized like `firmwareRoot` (§1). It is
**not** a reserved manifest field today — the manifest carries no app root until
apps exist. `translations_root` is the analogous anchor for translation blobs
and *is* reserved (zeroed) in the manifest, though translations are not built
yet either.

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
| module code | per module, in firmware image | yes (via manifest `code_hash`) |

## 9. Verification flow

**Boot (boardloader → bootloader → firmware):**
1. Boardloader: recompute model leaf from the boot header + `H(bootloader_code)`,
   fold `boot_header_merkle_proof` → `modelRoot`, verify signature. Jump to
   bootloader.
2. Bootloader: read the manifest at firmware start, `variant_leaf =
   SHA256(0x00 || manifest)`, fold `firmware_proof` → compare to `firmware_root`
   from its (boardloader-verified) boot header. Then for each manifest entry:
   `SHA256(code @ addr, size) == code_hash`. Jump to the entry module (secmon).
3. Kernel (opt, future): to load an app, fold the app's path → a future app root
   carried in the (bootloader-verified) manifest.

## 10. Implementation status

- **[impl]** hashing primitives + fold; manifest verify math
  (`firmware_manifest_authentic` / `firmware_verify_manifest` /
  `firmware_verify_manifest_entry` — variant leaf `H(0x00 || manifest)` folds to
  `firmware_root`, each entry's code verified vs `code_hash`);
  cross-validation harness (`tests/fw_merkle`).
- **[impl]** manifest at firmware start (linker `.manifest` region +
  `manifest_header.S`); no per-module header (module code committed directly);
  `fw_check_pq.c` / `wf_firmware_update_pq.c` drive off the manifest.
- **[impl]** `firmware_proof_nodes` in `boot_header_unauth_t` +
  `fw_check_pq.c` reads and folds it (11b); Python `BootHeaderUnauth` mirrors.
- **[impl]** build-time variant stamping (universal=2 / btc-only=3 / custom=1).
- **[impl]** custom firmware as a first-class tree variant (`FW_VARIANT_CUSTOM`,
  founder-zeroed app `code_hash` in the leaf; app founder-unbound + integrity-
  checked; `firmware_type` == variant; unprivileged, unlocked-bootloader-only;
  `--unsafe-fw` builds it). See §5.5.
- **[proto host]** founder tree over variants + per-variant proofs
  (`firmware_module.build_founder_tree`); manifest build (`build_manifest` /
  `fill_manifest` / `variant_leaf` + `authenticity_manifest`).
- **[design / TODO]** model tree → `modelRoot` (multi-model, non-empty
  `boot_header_merkle_proof`); app tree + its manifest app root; translations; nRF as a
  shared node; kernel/core split; production signing; whether the custom slot
  ships in the production field `firmwareRoot`.

## 11. Open questions

- Manifest reserved-region size + module alignment at firmware start.
- nRF: option 1 vs 2; is it ever genuinely per-variant?
- ~~`firmware_type` = variant marker + a derived custom/official bit~~
  **RESOLVED**: `firmware_type` IS the authenticated variant byte; custom-ness is
  the `FW_VARIANT_CUSTOM` variant, not a flag (see §5.5).
- Whether `boot_header_merkle_proof` (model tree) is ever populated (batched
  multi-model signing) or stays single-leaf.
- Kernel vs coreapp as separate modules (boot-flow change).
