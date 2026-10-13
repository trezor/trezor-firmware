# Firmware Merkle-tree cross-validation

The device (`sec/image`: `merkle.c`, `firmware_manifest.c`, `fw_variant.c`,
`boot_header_consent.c`; `nrf_image.c`), the nRF's MCUboot
(`image_pq.c`) and the host tooling (`trezorlib.merkle_tree`,
`trezor_core_tools`) must agree byte-for-byte, and a mismatch is silent: images
simply stop verifying. These harnesses compile the real device verification
code against a host SHA-256 and replay vectors produced by the tooling.

| script | checks |
| --- | --- |
| `run.sh` | the firmware root and every variant's accept/reject policy |
| `run_nrf.sh` | the nRF slot fold, its push gate and acceptance predicates |
| `run_founder_sig.sh` | the founder hybrid signature, with its negatives |
| `run_consent.sh` | the consent digest trezorlib puts on the wire is the one the bootloader and the firmware compute from the same release |

The harnesses are run by hand: nothing in the build or CI invokes them, they
need this branch's `trezorlib` on `PYTHONPATH`, and the nRF and
founder-signature scripts additionally need the sibling mcuboot checkout on its
PQ branch (they skip otherwise).

The nRF parsing invariants (see `docs/core/embed-arch/firmware-merkle-tree.md`)
are covered by negative tests in `nrf_crossvalidate.c`, which assert
*rejection* rather than merely "does not crash" — an over-read that happened to
land inside the staging area would otherwise pass unnoticed. Each test mutation
is asserted to leave the leaf unchanged, so it really is invisible to the fold.

## Coverage

What the vectors actually reach today, so the gaps are not mistaken for checks:

| covered | not covered |
| --- | --- |
| tree math, manifest folds, variant leaves (`merkle.c`, `firmware_manifest.c`, `fw_variant.c`) | `boot_header.c` — `boot_header_check_signature` is compiled by no harness, so the STM's own signature verify is cross-checked against nothing |
| the nRF's leaf, bounds discipline and acceptance predicates | `firmware_manifest_layout_valid` — the only bound on a custom app's `addr`/`size` before hashing |
| the founder signature scheme, via the nRF's `pq_image_verify` | `firmware_manifest_read_proof` — `crossvalidate.c` takes the proof from a side field of the vector, not from the manifest region the device parses |

A drift in the EC pre-hash, the sigmask-to-key mapping or the model-path fold
between the STM, the nRF and the signer would therefore go undetected.

## OTA fault injection

`core/tools/trezor_core_tools/firmware_pq_update.py` drives the same install as
`trezorctl`, but can inject the faults trezorctl deliberately cannot
(`make upload_pq_test UPLOAD_OPTS="--tamper ..."`).
