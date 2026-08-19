# Firmware Merkle-tree signing

Trezor firmware is authenticated against a **single signed Merkle root**. One
signature covers the bootloader, every firmware variant, and each variant's
modules. Verification is post-quantum ready (SLH-DSA alongside an EC signature)
and is split across the boot stages so each stage recomputes only the part of
the tree it is responsible for.

This document describes the on-flash and on-wire format and how it is verified.

## Overview

The founder signs one root, `modelRoot`, that spans the model's bootloader and
its firmware sub-tree. Verification is layered:

| Stage | recomputes | folds via | up to | trust anchor |
| --- | --- | --- | --- | --- |
| **boardloader** | boot-header leaf + `H(bootloader code)` | model path | `modelRoot` | verifies the **signature** |
| **bootloader** | firmware manifest (variant leaf) | firmware path | `firmwareRoot` | trusts `firmwareRoot` from the boardloader-verified boot header |

`firmwareRoot` is the root of the model's firmware sub-tree. It is carried as a
signed field inside the boot header (the model leaf), so the boardloader
authenticates it as part of the signature check, and the bootloader can then
fold the firmware sub-tree against a root it already trusts — no second signature
check. This root-embedding is the checkpoint that links the two stages.

Because the tree is content-addressed, a build produces a single root value that
can be compared against what a device displays, and a device can show what
changed between two roots (for example a new bootloader versus only a new app).

## Tree shape

```
modelRoot                                             [signed]
└── model leaf { hw_model, version, …, firmwareRoot } ← boot header (TRZQ)
        └── firmwareRoot                              (embedded, signed field)
              ├── variant manifest (universal)  { firmware_type,
              │        translations_root, module directory [secmon, app] }
              ├── variant manifest (bitcoin-only)
              ├── variant manifest (prodtest)
              └── variant manifest (custom)
```

Every edge is a Merkle fold (a child authenticates via a co-path up to the
root), except `firmwareRoot`, which is a field embedded in — and signed as part
of — the model leaf.

## Hashing primitives

Leaves and internal nodes are domain-separated:

- **Leaf:** `leaf(x) = SHA256(0x00 || x)`
- **Internal node:** `node(a, b) = SHA256(0x01 || min(a, b) || max(a, b))`
- **Proof fold:** starting from a leaf, `for sibling in proof: node = node(current, sibling)` — a sorted-pair authentication path.

The `0x00` / `0x01` prefixes prevent a proof for an internal node from being
replayed as a leaf and vice-versa. The device (`boot_header_merkle.c`) and the
host tooling (`trezorlib.merkle_tree`) implement these identically; a
cross-validation harness (`core/tests/fw_merkle`) replays vectors through both
to guarantee they agree byte-for-byte.

## Model layer (boardloader)

### Model leaf — the boot header

The model leaf is the authenticated boot header (`boot_header_auth_t`, magic
`TRZQ`) hashed together with the bootloader code:

```
leaf = SHA256(0x00 || auth_bytes[auth_size] || SHA256(bootloader_code))
```

Authenticated fields include the model identity (`hw_model`, `hw_revision`),
versioning and downgrade counters (`version`, `fix_version`,
`min_prev_version`, `monotonic_version`), the self-describing layout sizes, and
the checkpoint field **`firmware_root`** (32 bytes) — the root of this model's
firmware sub-tree.

### Model path

The boot header stores the co-path from the model leaf up to `modelRoot`
immediately after its authenticated part. The boardloader folds it to
`modelRoot` and verifies the founder signature over that root. A single-model
signed root uses an empty path (the model leaf is the root).

## Firmware layer (bootloader)

### Variant manifest — the firmware directory

Each firmware variant is described by a **manifest** placed at the very start of
the firmware image, before the module code. The manifest is the variant leaf of
the firmware sub-tree (`variant_leaf = SHA256(0x00 || manifest)`) and doubles as
a directory of the modules that make up the image. There is no separate
per-module header — each manifest entry commits its module's code directly.

Manifest (little-endian):

| offset | field | type | notes |
| --- | --- | --- | --- |
| 0 | `magic` = `TRZD` | u32 | firmware directory |
| 4 | `firmware_variant` | u32 | `fw_variant_t`; authenticated |
| 8 | `firmware_version` | 4×u8 | major, minor, patch, build |
| 12 | `translations_root` | 32 | root of translations (zero until present) |
| 44 | `module_count` | u32 | |
| 48 | `entry[module_count]` | — | 52 bytes each |

Entry:

| offset | field | type | notes |
| --- | --- | --- | --- |
| 0 | `module_type` | u32 | role: secmon / app (`fw_module_type_t`) |
| 4 | `flags` | u32 | `FW_MANIFEST_ENTRY_FLAG_*` (e.g. the boot entry) |
| 8 | `addr` | u32 | module code offset from the firmware region start |
| 12 | `chunk_size` | u32 | smart-hashing chunk size for `code_hash` |
| 16 | `size` | u32 | module code size |
| 20 | `code_hash` | 32 | chain hash over the module code (see below) |

The module set, count and roles are authenticated data. The bootloader iterates
the directory rather than hardcoding a role table, so adding or splitting modules
of known types requires only a re-sign, not a firmware-code change.

### Firmware path

The co-path from the variant leaf up to `firmwareRoot` is stored **in the
firmware image itself**, in the manifest region immediately after the manifest
(`firmware_manifest_proof_t`: a node count plus up to `FW_MANIFEST_PROOF_MAX_NODES`
nodes). It sits outside the variant leaf (the leaf covers only the manifest), so
there is no circularity, and it is unauthenticated storage because it is verified
by recomputation against the signed `firmware_root`.

Because the image carries its own firmware proof, the boot header stores no
firmware proof — only the device-written `firmware_type` provisioning marker. A
single-variant image uses an empty proof (the variant leaf is `firmwareRoot`).

### Module code commitment — smart-hashing chain

Each module's `code_hash` is a **chained hash** over the code, computed in
`chunk_size` chunks. This lets an over-the-air update authenticate each chunk of
a module against the signed `code_hash` as it streams, instead of only after the
whole module has landed.

```
seed      = SHA256(0x01 || size_le32)          # binds the total length
H         = seed
for k = n-1 .. 0:                              # n = ceil(size / chunk_size)
    H     = SHA256(0x02 || H || chunk_k)       # fold last chunk -> first
code_hash = H                                  # chunk 0 is outermost
```

Two distinct domain tags (`0x01` for the seed, `0x02` for each fold step) and the
length-bound seed keep the construction injective — the final chunk may be
partial, so modules need no padding. Folding last-to-first makes chunk 0
outermost, which matches forward-order streaming: a receiver holding the trusted
`code_hash` can verify chunk 0 first, then chunk 1, and so on. At boot the whole
chain is recomputed over the placed code and compared to `code_hash`.

### Firmware image layout

```
firmware.bin:
  [ manifest + firmware proof ]   offset 0 (reserved region FW_MANIFEST_REGION)
  [ secmon: code ]                (FLASH_BLOCK_SIZE aligned)
  [ app:    code ]                (kernel + coreapp)
```

The manifest region is a fixed reserved size at the image start; each entry's
`addr` is the authenticated offset of its module code. Modules keep their natural
flash-write alignment and are not padded to the hash chunk size.

## Over-the-air update

Installing new firmware is a two-phase exchange driven by the host:

1. **`FirmwareBegin`** carries the new signed boot header and the authenticated
   manifest (variant leaf + firmware proof). The device folds the manifest to the
   boot header's `firmware_root`, confirms with the user, stages the new boot
   header, and reboots so the boardloader installs it.
2. **Module streaming** sends the module code in transport blocks. Each block is
   a whole number of hash chunks; the device verifies the block against the
   smart-hashing chain *before* writing it to flash, rejecting a bad block early.
   The chain intermediate needed to verify a block travels inline on the upload
   message (`FirmwareUpload.prev_hash`); the innermost chunk of each module
   derives the seed. A final whole-tree verification is the backstop.

The transport block size is chosen independently of the hash chunk size, so the
wire granularity (round-trips, early-reject latency) can be tuned without
changing the signed commitment.

## Custom (unofficial) firmware

Custom firmware is a first-class variant, `FW_VARIANT_CUSTOM`, not a flag. The
founder signs one custom slot into `firmwareRoot` whose variant leaf is computed
with everything the creator controls set to zero — the manifest
`firmware_version` and the app (`FW_MODULE_APP`) entry's `size` and `code_hash`.
The app entry's role/placement and the entire secmon entry stay real, so the
founder still binds the secmon and the app's position. Because the creator-owned
fields fold as zero, the one signed slot accepts any creator app; the creator's
real values are kept on flash for integrity and display only.

The manifest therefore serves two roles, and the zero-for-fold substitution lives
in exactly one place (`boot_header_variant_leaf`, mirrored in the host signer):

- **Authenticity** (founder): recompute the variant leaf with the app fields
  zeroed and fold to `firmwareRoot`. This proves the secmon and structure are
  founder-authorized and that this is the sanctioned custom slot; the app itself
  is not founder-bound.
- **Integrity** (creator): the app code must hash to the on-flash `code_hash` —
  a corruption check, not app authenticity.

A custom image runs unprivileged (no secret or provisioning access, with a boot
warning), is storage-isolated because `firmware_type` equals the variant, and can
only be installed on an unlocked bootloader. `firmware_type_is_official()` is a
positive allow-list, so an unrecognized or glitched `firmware_type` is never
treated as official.

## Verification at boot

1. **Boardloader:** recompute the model leaf from the boot header and
   `H(bootloader code)`, fold the model path to `modelRoot`, verify the founder
   signature, and jump to the bootloader.
2. **Bootloader:** read the manifest at the firmware start, compute
   `variant_leaf = SHA256(0x00 || manifest)`, fold the firmware proof from the
   manifest region, and compare to `firmware_root` from the (boardloader-verified)
   boot header. The authenticated `firmware_variant` must equal the boot header's
   `firmware_type` — this pins the running variant to its storage domain, so a
   genuine but different variant cannot boot against another domain's secrets, and
   an unprovisioned device stays unbootable until an install stamps the variant.
   Finally, each module's code is verified against its entry's `code_hash`, and
   the boot entry module (the secmon) is launched.

## Storage summary

| item | location | authenticated |
| --- | --- | --- |
| `modelRoot` signature | boot header (SLH-DSA + EC) | is the signature |
| `firmware_root` | boot header, authenticated part | yes (in the model leaf) |
| model path | boot header, after the auth part | folded into the signed root |
| `firmware_type` | boot header, unauthenticated part | no (device-written) |
| firmware proof | firmware image, manifest region | no (verified by recompute) |
| variant manifest | firmware image start | yes (variant leaf under `firmwareRoot`) |
| module code | firmware image, per module | yes (via the manifest `code_hash`) |

## Firmware on the nRF co-processor

On models with a separate BLE co-processor (nRF), that chip's firmware runs on its
own MCU under its own MCUboot, so it cannot be covered by a firmware module's
`code_hash`. Instead it gets **its own slot in the model tree** — one slot per
co-processor, a peer of the boot header rather than something hanging off the
firmware sub-tree. There is no separate nRF signature: the one boot-header
signature over `modelRoot` already covers that slot.

### The leaf

The slot value is MCUboot's *own* image hash — the SHA-256 it computes for itself
and publishes in TLV `0x10`:

```
image_hash = SHA256(header ‖ payload ‖ protected TLVs)
leaf       = SHA256(0x00 ‖ image_hash)
```

Uniform for every co-processor image, classic (Ed25519, T3W1) or PQ-native
(founder, T3T2) — no per-model branch. MCUboot's hash range is exactly
"everything except the unprotected TLV area", which is the boundary the founder
material needs: it signs `modelRoot`, so it cannot lie inside its own preimage.
Taking MCUboot's definition instead of deriving an equivalent rule means the STM,
the nRF and the host signer commit to the same bytes without agreeing on anything
private, and neither verifier hashes the image twice. Committing a
collision-resistant hash commits the bytes, so this is no weaker than hashing the
range directly.

Because the value is a bare 32 bytes, it is foldable on its own: a device can
establish *which* co-processor image a release expects without holding the image —
fold `H(0x00 ‖ hash)` through the co-path and compare against `modelRoot`.

### The unprotected area is not covered by the fold

The hash stops at the protected TLVs, so the fold proves nothing about the
unprotected TLV area — which is precisely where both schemes keep their signature
records. Anything that must be trusted there is checked explicitly, in two layers:

- **structure** — a per-scheme whitelist: exactly the expected records, no
  duplicates, right lengths, ending precisely at `tlv_end`. A rogue TLV added
  there leaves leaf, `modelRoot` and signature all intact, so only a shape check
  catches it. The two sets are:

  | scheme | unprotected records |
  | --- | --- |
  | classic | `0x0010` hash (32), `0x00A0` + `0x00A1` Ed25519 (64 each) |
  | founder | `0x0010` hash (32), `0x00A4`/`0x00A5` SLH-DSA, `0x00A6`/`0x00A7` Ed25519, `0x00A8` co-path (whole 32-byte nodes) |

  Both are **exact**, and deliberately stricter than the co-processor's own
  `allowed_unprot_tlvs`, which also tolerates KEYHASH, PUBKEY, other digests and
  the encryption TLVs. Being stricter can only refuse an image the co-processor
  would have taken, never accept one it would refuse — and refusing is the safe
  direction, since the alternative is erasing its only slot for an image it then
  rejects. The sets match what the signers actually emit: for classic, imgtool
  runs *without* a key (so it contributes only the hash TLV) and
  `insert_signatures.py` appends exactly the two signature records.
- **acceptance** — the co-processor's own verdict, predicted: for founder images
  the four records are byte-compared against the boot header's copies (possible
  because there is one signing per release); for classic images the two Ed25519
  records are verified against the nRF's own key pool, selected by the sigmask
  from the *protected* area.

The STM runs both before pushing, where they are a prediction that stops it
erasing a working co-processor for an image that would then be refused — on a
BLE-only device that is the host link, so it would be a remotely triggerable
brick. The co-processor runs them at boot, where they are the verdict.

That predicate is stronger than a wider leaf would be: "these bytes were signed"
becomes "the co-processor will accept these bytes". A model whose nRF is PQ-native
has no classic key pool and therefore *refuses* classic images rather than
accepting them unverified.

The classic key pool is **per model** (`MODEL_NRF_LEGACY_KEYS_*` in the model
header), unlike the founder root keys in `sec/root_keys.h`, which are one ceremony
covering every model. `root_keys_check.py` compares every copy against MCUboot's,
including order — the sigmask selects by index, so a reordering leaves the sets
equal while making the STM predict the wrong keys.

### Bounds discipline

The unprotected TLV area's declared extent (`it_tlv_tot`) and every record length
inside it are covered by no signature and no hash. With the leaf no longer
reaching them, the parser's bounds checks stop being belt-and-braces and become
the *only* defence. Four invariants:

1. **A declared extent that overruns the image is REJECTED, not clamped.**
   Clamping is safe against an over-read but not against a brick: MCUboot's
   generic validate takes `tlv_end` straight from `it_tlv_tot`
   (`bootutil_tlv_iter_begin` does not clamp), reads past the image into the slot,
   and refuses the image. An STM that clamped would predict acceptance, erase the
   co-processor's only slot, and be wrong. A well-formed image has
   `prot_end + it_tlv_tot == image_len` exactly, so nothing legitimate is refused.
2. **A record's declared length is checked before the read, not after** —
   `p + 4 + len > tlv_end` rejects, and only then is the value read.
3. **All offset arithmetic is 64-bit.** 16-bit lengths added to 32-bit offsets are
   summed in `uint64_t`, so no sum can wrap into a small value that passes a naive
   bound.
4. **A trailing stub too small to be a record is a failure, not a stop.** Silently
   ignoring a partial record at the end would let one be appended.

All four are covered by negative tests in `nrf_crossvalidate.c`, which assert
*rejection* rather than merely "does not crash" — an over-read that happened to
land inside the staging area would otherwise pass unnoticed. Each test mutation is
asserted to leave the leaf unchanged, so it really is invisible to the fold.

> The nRF's own `pq_parse_layout` still clamps here rather than rejecting. That is
> not exploitable, because its generic validate refuses the image anyway, but the
> two should be aligned.

### Where it lives

| implementation | file |
| --- | --- |
| STM (verify + push gate) | `core/embed/io/nrf/nrf_image.c` |
| nRF (its own MCUboot) | `bootloader/mcuboot/boot/bootutil/src/image_pq.c` |
| host signer | `core/tools/trezor_core_tools/nrf_tree.py` |

All three must agree byte-for-byte; a mismatch is silent (images simply stop
verifying), so they are cross-validated against shared vectors in
`core/tests/fw_merkle`.
