# PQ secure boot hardware tests (T3W1)

Standalone hardware test suite for the Merkle-tree secure boot stack and the
legacy->PQ migration. The plan it implements:
<https://claude.ai/artifact/NM2EJTGPnQtjFPPauEMECd>

## Fixtures

`build_fixtures.py` builds every binary the tests flash or install, from three
source branches, each in its own persistent worktree under `work/`:

| source | default ref | builds |
| --- | --- | --- |
| `legacy` | `tychovrahe/debuglink/early` (main + early debuglink) | boardloader, bootloader, universal and btc-only firmware |
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

- **Storage kept across reboots** without an edit: the debug boot wipe is the
  opt-in `--boot-wipe` build option on every source branch, and the builder
  does not pass it. All three branches also start USB and debuglink before the
  boot PIN prompt, so a PIN-locked unit can be driven over debuglink.
- **Optiga disabled** in every firmware build (`--disable-optiga`): each wallet
  set-up advances its security counter, which lives in the chip and survives
  `flash-erase`. Storage then takes its non-Optiga path in all of legacy,
  intermediary and PQ alike; a release-style run with Optiga belongs to the
  manual pass.
- **Intermediary stamp per variant.** The intermediary stamps `UNIVERSAL`
  unconditionally; a btc-only unit would lose its seed. Skipped once the branch
  fixes it.
- **Versions**, so the sets install in a meaningful order. The boot header
  `version` is the release version (= firmware version), stamped by the
  signer; the floors are release numbers from the firmware `version.h`. The
  bootloader column is the bootloader's own compile-time version (Features):

| set | firmware | bootloader | floor |
| --- | --- | --- | --- |
| legacy | 2.13.0 | 2.1.18 (monotonic 2) | |
| intermediary | 2.13.1 | embeds A | |
| release-A | 2.14.0 | 2.1.19 (monotonic 3) | |
| release-B | 2.14.1 | 2.1.20 | |
| release-B-fix | 2.14.2 | 2.1.20 | fix_version 2.14.1 |
| release-C-minprev | 2.14.3 | 2.1.21 | min_prev_version 2.14.1 |
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

## Tests

Run from this directory (it carries its own `pytest.ini`):

```sh
pytest                         # offline: the fixture set itself, no device
pytest --hw                    # flash and drive the attached T3W1
pytest --hw -k migration       # one area
pytest --hw --operator -s      # with a person to rescue a stuck phase 2
pytest --hw -m "not cut"       # everything but the SWD power-loss cuts
pytest --hw --nrf-jlink 933001122   # also reset the nRF over J-Link (serial or "auto")
```

### The nRF over J-Link

Flashing the STM does not touch the nRF, so without help each run inherits
whatever nRF the previous one left: an install whose nRF is already current
pushes nothing, and the push tests (MG-12) skip. With `--nrf-jlink`, every
baseline first writes a known application image to the nRF over a J-Link wired
to it (`Unit.flash_nrf`, `nrfjprog`):

- a legacy baseline gets the image the legacy firmware embeds
  (`legacy/trezor-ble-dev.bin`), so the legacy boot finds it current;
- a PQ baseline gets its release's own image, so installing another release
  is a real push;
- MG-12 writes `inputs/nrf-1.0.0-dev.bin` while the legacy bootloader runs, so
  the intermediary (which embeds 1.0.1) has a push to cut.

Only the application slot (0xE000, 432 KB) is written, page by page: MCUboot,
`custom_data` and the bond storage are left alone. MCUboot runs single-app and
checks only the signature, so any dev-signed image boots, older ones included.
The helper resets the nRF and checks its PC is inside the application slot,
so an image MCUboot refuses fails the run instead of looking like a skip.

`--hw` needs openocd with an ST-Link on the unit (the tests flash through
`xtask flash` / `flash-erase`) and the unit on USB. Every test builds its own
starting state from a full erase, so tests are independent and any order works.

| file | covers (plan IDs) |
| --- | --- |
| `test_fixtures.py` | every release variant verifies; versions climb; floors; intermediaries embed A; btc-only salting; every cut point resolves in its ELF |
| `test_install.py` | BT-01, BT-05, IN-02, IN-10, IN-11, IN-12, IL-01, IL-02, NR-01, VR-05, VR-06, FW-01, header-only reinstall |
| `test_tamper.py` | the wire tamper matrix: IN-03, IN-05, IN-06, IN-07, IN-08, IN-13, IN-14, IL-02, NR-03, MG-19 (PQ half) |
| `test_floors.py` | VR-01 (`burns`), VR-03, VR-04 |
| `test_power_loss.py` | PL-01…04, PL-06…08, MG-12…15 (`cut`) |
| `test_migration.py` | MG-01, MG-03, MG-04/05, MG-09; a variant change after migration wipes |
| `test_scenarios.py` | WP-01, MG-19 (legacy half) |
| `test_pin.py` | MG-02, MG-04, MG-07 (PIN and wipe code at boot, over debuglink) |

The tamper cases (`pqhw/tamper.py`) are the manual wire harness's
(`firmware_pq_update.py --tamper`), with the same expected messages, restated
as functions over the upload the flows send. Every refusal is followed by a
recovery check: a refusal before the confirm leaves the firmware and seed
untouched, a refusal in phase 2 is cured by the honest install.

Two device facts shape the suite:

- **Seeds are loaded without a PIN**, except in `test_pin.py`, so that reboots
  need no unlock. The storage salt binds `firmware_type` either way, so seed
  checks are just as strong. Debug builds start USB and debuglink before the
  boot PIN prompt, so the PIN tests tap the lockscreen and type the PIN (or the
  wipe code) over debuglink (`device.unlock_lockscreen`).
- **A bootloader prompt is detected by silence.** The bootloader sends no
  ButtonRequest and its debuglink reports no layout content, so a request that
  has not been answered after `--stall` seconds (default 6) counts as waiting on
  a confirmation; the test taps the right action-bar button and records it.
  Validated on the bootloader emulator (prompt, tap, refusal without a tap).
  If a slow verification is ever misread as a prompt, raise `--stall`.

## Flow report and screenshots

A `--hw` run writes `reports/<timestamp>/index.html`: a summary table, then
per test its steps in order (every reconnection, every bootloader tap with
the screen being confirmed, each install phase) with a screenshot each, the
failure traceback and the captured log. The path is printed at the end of
the run; `--report-dir` moves it, `--no-screens` keeps the steps but skips
the pictures.

Screenshots are read over SWD (`pqhw/screen.py`), because neither debuglink
returns pixels on hardware. openocd reads which GFXMMU virtual buffer the LTDC is scanning
(layer-1 `CFBAR`), dumps it, then reads every 8th line and `CFBAR` again; a
capture that saw a swap or a redraw is taken again, up to three times. A
screen that never settles keeps its last capture, marked in the report as
possibly mixing two frames. The CPU
keeps running (pausing it mid-install would risk host timeouts), so a picture
shows the screen at the moment of the read: the step itself on a screen that
waits for input, possibly the next screen on a transient one. The SWD clock
defaults to 24 MHz, an ST-Link V3's maximum (about 3 s per capture); lower it
with `PQHW_SWD_KHZ` on a long cable or an older probe.
`python -m pqhw.screen out.png` takes one capture and prints how long it took. The boardloader does not drive the
display, so a step during it shows the error instead of a picture.

## Power-loss cuts

`pqhw/cutpoint.py` makes a power cut at a chosen instruction: openocd sets a
hardware breakpoint there, waits for the unit to halt, resets it (`reset
halt`, checked to land on the boardloader's reset handler) and lets it boot.
Cuts are named as call sites, `caller>callee`: `before` halts on the call
instruction, `after` on the one following it, `during` lets the callee run a
few seconds first. Not on the callee's own entry: on hardware a halt on a
function's first instruction behaved as if the function had already run (a
cut "before `ucb_stage_arm`" still armed the swap; a cut on the `bl` in the
caller did not). After each cut the boot is traced: breakpoints on the
boardloader's `boot_ucb_read` and the bootloader's `boot_ucb_write` record
what the firmware itself read and wrote. Debugger reads of the UCB are not
trusted: they disagreed with what the boardloader read at the same moment. Addresses come from the ELF of the code that will run the
function, which the builder stages next to each image and checks byte for
byte against it: `release-*/T3W1/bootloader.elf`, and
`intermediary/{kernel,secmon}-<variant>.elf`. A cut in a bootloader that only
boots later (B's, after the boardloader swap) is armed once the old one has
stopped, since the same address is other code in the old image.

While a cut is armed, openocd holds the ST-Link: steps recorded meanwhile have
no screenshot ("SWD probe held by the cut point"). A reset is not a brown-out
in the middle of a flash write; PL-05 (during the boardloader's copy) needs a
switched power supply and is not automated.
