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

`firmwareRoot` is an ordinary **internal node** of the single tree,
but it is also **materialized as a field** in its parent node (a checkpoint),
so a lower domain can verify its subtree locally against a root it already trusts
without re-walking to `modelRoot` or re-checking the signature.

The founder's build system produces `modelRoot`; the founder compares it against
the value shown on their Trezor, and the Trezor can show what changed since last
time (e.g. a new bootloader vs. just a new Solana app).

## 2. Tree shape

```
modelRoot                                            [signed]
├── modelIntNode…
│   ├── model leaf  { hwModel, version, fixVersion, …,
│   │                 firmwareRoot, bootloaderHash }      ← boot header (TRZQ)
│   │         └── firmwareRoot                            (materialized field)
│   │               ├── variant manifest (universal)  { firmwareType,
│   │               │        translationsRoot, hashDirectory[secmon,kernel,core] }
│   │               ├── variant manifest (bitcoin-only)
│   │               └── variant manifest (prodtest)
│   └── nrf leaf     (self-verified model-level peer, variant-agnostic — see §6)
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
the firmware image's **manifest region**, immediately after the manifest
(`firmware_manifest_proof_t`: `node_count` +
`nodes[≤ FW_MANIFEST_PROOF_MAX_NODES=4]`), so the image carries its own proof and
**no proof is stored in the boot header**. It sits OUTSIDE the variant leaf (the
leaf is `H(0x00 || manifest)`, covering only the manifest), so there is no
circularity. Verified by recomputation against the (signed) `firmware_root`, so
unauth is safe. Baked into the image by the signer (`firmware_pq_sign`). `count =
0` ⇒ single-variant (`variant leaf == firmwareRoot`, identity fold) — backward
compatible. This is the *middle* segment of the one tree; `boot_header_merkle_
proof` is the *top* segment.

Because the proof rides in the image, a directly-flashed `firmware.bin` needs no
proof baked into the bootloader (only `firmware_type` for provisioning), and OTA
phase 1 no longer writes a proof to the boot header — it only stamps
`firmware_type`.

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

## 6. nRF placement — **[design]**

The nRF (BLE co-processor) firmware runs on a **separate chip** and is
**variant-agnostic and model-specific**. It boots on its own MCU *before* the STM
can inspect it, and a hash the nRF *reports back* is not a trustworthy check — so
the STM cannot verify the running nRF firmware top-down. Security of the link
rests on **THP + pairing/HMAC**; the nRF is treated as an untrusted comms party.

The nRF is therefore a **self-verifying, model-level peer** of the STM in the one
founder tree — NOT a node under `firmwareRoot`, and NOT embedded in a variant
manifest:

- **Root of trust on the nRF side.** The nRF has its own two stages — an **nRF
  bootloader** (founder pubkey, factory-provisioned, exactly like the STM
  boardloader) plus an updatable **nRF app**. The nRF app carries its own
  boot-header-equivalent + Merkle proof, and the nRF bootloader verifies its
  (PQ / SLH-DSA) signature at **install and boot**. SLH-DSA on the nRF MCU is
  feasible (~16 kB signature — optionally MCU-supplied — + ~11 kB code, ~2 kB
  RAM, ~75 ms).
- **One founder root.** The nRF app's leaf proves into the **same founder root**
  (`modelRoot`) as the STM model leaf: one founder key signs both branches, and
  the STM boardloader and the nRF bootloader both hold that key. This is mainly
  founder/organisational unification — the *authoritative* nRF check is on the
  nRF chip, at boot.
- **STM verifies only at install.** During a bootloader-mediated nRF install the
  STM has the nRF bytes and the founder pubkey, so it verifies the nRF app's
  founder signature then, rejecting a bad binary early (defense-in-depth).
  Verifying that signature needs only the founder pubkey, not a materialised
  `modelRoot`. At boot the STM cannot check the nRF — that is the nRF
  bootloader's job.

**Install path.** The nRF firmware is **not embedded** in kernel+coreapp; it is
delivered and updated **through the STM bootloader** — staged to non-volatile
memory before transfer to the nRF chip, so an interrupted update bricks neither
side. Doing it in the bootloader (not the firmware) means an nRF update needs no
firmware install and reuses the same staging mechanism. Motivation: free flash on
constrained models (U585 / Pico) and app space on T3W1. Pairing keys (derived
from `secret`) are available to the bootloader.

**Downgrade — coupled monotonic.** A drift between the STM firmware and the nRF
firmware could make a **comms-incompatible** pair, so their `monotonic_version`
is kept **matched**: the nRF app and the STM boot header carry the same monotonic,
and a coupled release bumps both. Enforcement needs **no new persistent state** —
it falls out of three existing/planned pieces:

1. **Install-time equality check.** The bootloader (which installs the nRF and
   has verified its signature) requires `nRF.monotonic == boot_header.monotonic`;
   a mismatched pair can never be installed.
2. **STM self-rollback (existing).** The boardloader already pins the boot-header
   monotonic non-decreasing (`write_/check_bootloader_min_version`), so the STM
   side — and thus the matched nRF — can't roll back.
3. **nRF self-rollback (planned).** The nRF bootloader keeps *its* monotonic
   non-decreasing, so the nRF can't be downgraded out-of-band on its own chip.

Together the pair is pinned and matched forever, with the STM boot-header
monotonic as the single reference — no recorded nRF version needed (that would
only be required for *decoupled* per-side floors, and couldn't be trusted from a
runtime nRF report anyway). The coupled install must be **ordered** (commit/verify
the nRF before bumping the boot header) so a partial two-chip update leaves a
consistent pair, not a stranded mismatch. This is a **version-axis** coupling for
compatibility, not a tree coupling (no multi-version-tree signing). Cost: no
independent nRF version bumps — an nRF-only fix still needs a coupled monotonic
bump, i.e. a re-signed boot header (cheap via the header-only update path) even if
the STM code is unchanged.

**Today (T3W1):** the nRF stays **embedded** in kernel+coreapp (`.nrf_app`),
covered transitively by that module's `code_hash` and version-locked one-to-one
with the firmware. The self-verifying peer split above is the target for
flash-constrained models.

## 7. Storage summary

| item | where | authenticated? |
| --- | --- | --- |
| `modelRoot` signature | boot header unauth (`slh`/`ec` sigs) | is the signature |
| `firmware_root` | boot header **auth** | yes (in model leaf) |
| model path (`boot_header_merkle_proof`) | boot header, after auth | folded into signed root |
| `firmware_type` | boot header **unauth** | no (device-written) |
| firmware path (`firmware_proof`) | **firmware image** manifest region (after the manifest) | no (verified by recompute) |
| variant manifest | **firmware image start** | yes (leaf under `firmwareRoot`) |
| module code | per module, in firmware image | yes (via manifest `code_hash`) |

## 8. Verification flow

**Boot (boardloader → bootloader → firmware):**
1. Boardloader: recompute model leaf from the boot header + `H(bootloader_code)`,
   fold `boot_header_merkle_proof` → `modelRoot`, verify signature. Jump to
   bootloader.
2. Bootloader: read the manifest at firmware start, `variant_leaf =
   SHA256(0x00 || manifest)`, read `firmware_proof` from the manifest region
   (right after the manifest) and fold it → compare to `firmware_root` from its
   (boardloader-verified) boot header. **Variant pin:** the authenticated
   `firmware_variant` must equal the boot-header `firmware_type` (the
   storage-domain identity), so a genuine-but-different variant (which folds fine)
   cannot boot against another domain's seed, and an unprovisioned
   (`firmware_type==0`) or unmatched device stays unbootable until a real install
   stamps the variant. Then for each manifest entry:
   `SHA256(code @ addr, size) == code_hash`. Jump to the entry module (secmon).

## 9. Implementation status

- **[impl]** hashing primitives + fold; manifest verify math
  (`firmware_manifest_authentic` / `firmware_verify_manifest` /
  `firmware_verify_manifest_entry` — variant leaf `H(0x00 || manifest)` folds to
  `firmware_root`, each entry's code verified vs `code_hash`);
  cross-validation harness (`tests/fw_merkle`).
- **[impl]** manifest at firmware start (linker `.manifest` region +
  `manifest_header.S`); no per-module header (module code committed directly);
  `fw_check_pq.c` / `wf_firmware_update_pq.c` drive off the manifest.
- **[impl]** `firmware_proof` embedded in the firmware image's manifest region
  (`firmware_manifest_proof_t`, after the manifest, OUTSIDE the leaf);
  `fw_check_pq.c` / `wf_firmware_update_pq.c` read + fold it (11b) via the
  bounds-checked `firmware_manifest_read_proof`; the signer bakes it in, the boot
  header carries no proof. Python `firmware_module` mirrors (`install_manifest_
  proof` / `read_manifest_proof`).
- **[impl]** build-time variant stamping (universal=2 / btc-only=3 / custom=1).
- **[impl]** custom firmware as a first-class tree variant (`FW_VARIANT_CUSTOM`,
  founder-zeroed app `code_hash` in the leaf; app founder-unbound + integrity-
  checked; `firmware_type` == variant; unprivileged, unlocked-bootloader-only;
  `--unsafe-fw` builds it). See §5.5.
- **[proto host]** founder tree over variants + per-variant proofs
  (`firmware_module.build_founder_tree`); manifest build (`build_manifest` /
  `fill_manifest` / `variant_leaf` + `authenticity_manifest`).
- **[design / TODO]** model tree → `modelRoot` (multi-model, non-empty
  `boot_header_merkle_proof`); translations; nRF as a self-verified model-level
  peer (own boot-stage + proof, STM-checked only at install, monotonic coupled —
  §6); kernel/core split; production signing; whether the custom slot ships in
  the production field `firmwareRoot`.

## 10. Open questions

- Manifest reserved-region size + module alignment at firmware start.
- ~~nRF: shared node under `firmwareRoot` vs `nrfRoot` peer; who verifies?~~
  **RESOLVED** (see §6): self-verified model-level peer under `modelRoot` (nRF
  bootloader holds the founder key), STM verifies only at install, monotonic
  coupled to the boot header via an install-time equality check + both-sides
  self-rollback (no recorded nRF version). Remaining: the exact nRF
  boot-header-equivalent layout, and the ordered two-chip install commit.
- ~~`firmware_type` = variant marker + a derived custom/official bit~~
  **RESOLVED**: `firmware_type` IS the authenticated variant byte; custom-ness is
  the `FW_VARIANT_CUSTOM` variant, not a flag (see §5.5).
- Whether `boot_header_merkle_proof` (model tree) is ever populated (batched
  multi-model signing) or stays single-leaf.
- Kernel vs coreapp as separate modules (boot-flow change).
