# PQ secure boot hardware tests (T3W1)

Standalone hardware test suite for the Merkle-tree secure boot stack and the
legacy->PQ migration. The plan it implements:
<https://claude.ai/artifact/NM2EJTGPnQtjFPPauEMECd>

## Fixtures

`build_fixtures.py` builds every binary the tests flash or install, from three
source branches, each in its own persistent worktree under `work/`:

| source | default ref | builds |
| --- | --- | --- |
| `legacy` | merge-base of the intermediary and `main` | boardloader, bootloader, universal and btc-only firmware |
| `pq` | `tychovrahe/pq/bootloader12` | releases A, B, B-fix, C-minprev, E-mono |
| `intermediary` | `tychovrahe/pq/intermediary_exp` | universal and btc-only intermediaries, embedding release A |

Outputs go to `fixtures/`, a worktree of the local orphan branch
`tychovrahe/pq/hw_fixtures`. `fixtures/manifest.json` records, for every file,
the source commit, build flags, source edits and sha256.

```sh
python core/test_pq_hw/build_fixtures.py                    # all targets
python core/test_pq_hw/build_fixtures.py --only release-A   # A and the intermediaries
python core/test_pq_hw/build_fixtures.py --ref pq=<ref>     # build from another ref
python core/test_pq_hw/build_fixtures.py --commit           # commit the set
```

Run it inside the nix-shell with the repo `.venv` present. Logs are in
`work/logs/<target>.log`.

### What the builds change

Applied to the scratch worktrees only:

- **Storage kept across reboots.** Firmware debuglink exists only under
  `__debug__`, and `boot.py` wipes storage on every hardware boot of such a
  build, which would defeat every seed check.
- **Intermediary stamp per variant.** The intermediary stamps `UNIVERSAL`
  unconditionally; a btc-only unit would lose its seed. Skipped once the branch
  fixes it.
- **Versions**, so the sets install in a meaningful order:

| set | firmware | bootloader | floor |
| --- | --- | --- | --- |
| legacy | 2.13.0 | 2.1.18 (monotonic 2) | |
| intermediary | 2.13.1 | embeds A | |
| release-A | 2.14.0 | 2.1.19 (monotonic 3) | |
| release-B | 2.14.1 | 2.1.20 | |
| release-B-fix | 2.14.2 | 2.1.20 | fix_version 2.1.20 |
| release-C-minprev | 2.14.3 | 2.1.21 | min_prev_version 2.1.20 |
| release-E-mono | 2.14.4 | 2.1.22 | monotonic 4 |

Releases from B on release a second nRF build, frozen as a fixture input
(`fixtures/inputs/nrf-1.1.3-dev-bare.bin`, with a JSON note of how it was
built), so A -> B is a real nRF push (1.0.1 -> 1.1.3). The builder checks the
released image carries that version.

Every `--bootloader-devel` legacy build uses the dev vendor header, whose
`fw_type` is universal whatever `--btc-only` says, so the btc-only legacy
firmware and intermediary carry a generated dev-signed vendor header with
`fw_type 3`.

The build's dependency tracking misses headers included from assembly
(`header.S`, `manifest_header.S`), so the builder touches every file that
includes a `version.h` before building, and afterwards asserts that each image
carries the requested versions and floors.

The intermediaries embed release A's exact bootloader bytes (whose header
commits to A's `firmware_root`) and A's nRF image; the builder checks both are
present in the output and rebuilds the intermediaries whenever A is rebuilt.

### Resetting a unit

`xtask flash-erase -m T3W1` erases the whole flash, which also resets the
bootloader monotonic counter, so a unit can return to the legacy baseline after
a migration or after release E.
