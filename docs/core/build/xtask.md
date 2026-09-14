# Building with xtask

`xtask` is the workspace automation tool for building, flashing and testing Trezor
firmware. The central command is `xtask build`.

## Quick start

```sh
xtask build firmware -m t3w1            # release firmware for T3W1
xtask build firmware -m t3w1 -e         # emulator build
xtask build firmware -m t3w1 -p test    # apply the "test" preset
xtask build bootloader -m t3t1 -b revE  # specific board revision
```

Both `<project>` and `-m <model>` are always required. `--board` is optional and
defaults to the model's `default_board`.

## The `xtask build` command

```sh
xtask build <project> -m <model> [options]
```

- `<project>` — what to build: `bootloader`, `boardloader`, `bootloader_ci`,
  `firmware`, `prodtest`, `kernel`, `secmon`.
- `-m / --model <model>` — target model, e.g. `t3w1`, `t3t1`, `t2b1`, `d001`.
- `-b / --board <board>` — board revision; defaults to the model's
  `default_board`.
- `-e / --emulator` — build the unix emulator instead of device firmware.
- `-p / --preset <name>` — apply a named build preset (see [presets.toml](#presetstoml--xtaskspresetstoml)).
- Further `--<option>` flags are listed under [Build options](#build-options).

## Other xtask commands

- `xtask clippy` / `xtask check` — same arguments as `build`, but run clippy or
  `cargo check`.
- `xtask test <packages...>` — run unit tests for the given packages.
- `xtask clean` — remove build artifacts.
- `xtask fmt` — format Rust sources with rustfmt.
- `xtask flash <project> -m <model>` — flash a built binary to a connected
  device via OpenOCD. `--combined` flashes the whole boot chain instead, from
  the image `xtask combine` produced.
- `xtask flash-erase [section] -m <model>` — erase a flash section (`all`,
  `boardloader`, `bootloader`, `firmware`, `storage`).
- `xtask reset -m <model>` — reset the connected device.
- `xtask upload <project> -m <model>` — upload firmware/prodtest to a running
  device.
- `xtask combine <project> -m <model>` — combine the boot chain, from the
  boardloader up to this project, into a single flashable binary. Flash it with
  `xtask flash <project> -m <model> --combined`.
- `xtask release [-m <model>]` — cut a complete pq_secure release: every
  variant, folded into one signed tree (see
  [pq_secure releases](#pq_secure-releases)).

## Build options

Most options are boolean — you can pass `--btc-only=true` or `--btc-only=false`.
`--btc-only` with no value is shorthand for `true`. If you don't mention the
option at all (and no preset sets it), it resolves to `false`:

```text
--btc-only            # same as --btc-only=true
--btc-only=false      # explicitly disabled
                      # (omitted entirely → false, unless a preset sets it)
```

A few options take a value from a fixed set instead. `--dbg-console` is one of
`none`, `vcp`, `swo`, `system-view`, and you must always supply the value — it
cannot be used bare:

```text
--dbg-console vcp     # ok
--dbg-console         # error: a value is required
```

- `--debug` — debug build (release by default).
- `--btc-only` — Bitcoin-only firmware.
- `--production` — production build (signed, no dev keys).
- `--frozen` — embed frozen MicroPython modules.
- `--pyopt` — optimize MicroPython bytecode (on by default).
- `--debug-link` — enable debug link (on by default when `pyopt` is off).
- `--dbg-console <none|vcp|swo|system-view>` — debug console backend.
- `--disable-animation` — disable UI animations.
- `--bootloader-devel` — use development bootloader.
- `--force-bootloader-upgrade` — force bootloader upgrade on next boot.
- `--asan` — enable AddressSanitizer.
- `--source-lines` — include MicroPython source lines.
- `--perf-overlay` — show UI performance overlay.
- `--disable-optiga` — disable OPTIGA support.
- `--disable-tropic` — disable TROPIC support.
- `--mem-perf` — MicroPython memory performance measurements.
- `--benchmark` — include crypto benchmarks.
- `--log-stack-usage` — log stack usage.
- `--block-on-vcp` — blocking VCP writes for reliable debug output.
- `--emit-memory-analysis` — emit type/stack size analysis.
- `--timings` — output cargo timings.
- `--verbose` — verbose cargo output.
- `--xbuild-trace` — log build script progress (executed commands and timings).
- `--apps` — enable external app loading.
- `--n1w1` — enable N1W1 support.
- `--miniscript` — enable experimental Miniscript support.
- `--unsafe-fw` — enable unsafe firmware features.
- `--storage-insecure-testing-mode` — insecure storage test mode (forbidden with
  `--production`).

## Configuration files

The build is driven by four kinds of TOML files. Together they define *what* a
model offers, *which* parts of it a project uses, and *how* build options turn
into cargo features.

### model.toml — `models/<model>/model.toml`

Describes one Trezor model (T3W1, T3T1, D001, ...). It defines the MCU (e.g.
`stm32u5g`), which selects the compiler target, and the `default_board` used
when `--board` is omitted. It lists the model's intrinsic capabilities (cargo
features) that projects may opt into, marks whether the model uses a secure
monitor (`secmon`), and may carry per-project feature exclusions under
`[project_overrides]`.

### {board}.toml — `models/<model>/boards/<board>.toml`

Describes one hardware revision of a model (e.g. `revC`, `revE`). It points to
the C header that configures the board's pins and peripherals, optionally
provides a separate header for emulator builds, and lists peripherals (display,
touch, backlight, optiga, ...) together with their driver crates.

### project.toml — `projects/<project>/project.toml`

Describes one buildable project (firmware, bootloader, kernel, ...). The `uses`
list is a whitelist of model/board capabilities this project actually needs.
`elf_sections` selects which ELF sections end up in the final binary. The
`[build-options]` table maps each build option value to cargo features for this
project. STM32F4 split-bank layout and secmon body/header sections may also be
defined here.

### presets.toml — `xtask/presets.toml`

Shared, versioned preset definitions. The file is a collection of named
presets, each made of one or more `[[<name>]]` fragments. Two names are
special:

- `[[defaults]]` — base options applied before any named preset.
- any other name (e.g. `[[test]]`, `[[dev]]`) — applied only when selected with
  `-p <name>`.

A fragment looks like:

```toml
[[dev]]
when = { emulator = false, project = ["firmware", "prodtest"] }
dbg-console = "swo"
debug = true
pyopt = false
```

**The `when` filter.** Each fragment may carry an optional `when` table that
decides whether the fragment applies to the current build. The fields are:

- `model` — array of models (e.g. `["t3w1", "t3t1"]`); matches if the build's
  model is in the list.
- `project` — array of projects; matches if the build's project is in the list.
- `emulator` — boolean; matches the build's emulator flag.

Fields are combined with **AND** (all must match); values inside one field are
combined with **OR**. A field omitted from `when` matches everything, so a
fragment without `when` always applies.

**Processing order.** For a given preset name, all fragments are visited
**top to bottom** in file order. Each fragment whose `when` matches the current
build contributes its options; fragments that do not match are skipped. This
lets you write general defaults first and tighten them for specific cases later
in the file — for example a `[[dev]]` block for all hardware builds followed by
a more specific `[[dev]]` block for `firmware`/`prodtest` only.

**How values override.** Options are merged with an overlay: a value set by a
later matching fragment replaces the same option set by an earlier one. Options
that a fragment does not mention are left untouched. So fragments do not need
to repeat every option — only the ones they want to change. For example:

```toml
[[test]]
debug = true
pyopt = true                  # applies to every test build

[[test]]
when = { emulator = true }
pyopt = false                 # emulator test builds override pyopt only
```

A hardware `test` build gets `pyopt = true`; an emulator `test` build gets
`pyopt = false` (and still inherits `debug = true` from the first fragment).

**Across the two files.** `presets.toml` is processed first, then
`user-presets.toml`. Within each file the rules above apply. The user file can
add new presets, or add fragments to an existing preset name to override or
extend the shared definition.

### user-presets.toml — `xtask/user-presets.toml`

Optional, git-ignored personal overrides. Same format as `presets.toml`. Can
define new local presets or override values of shared presets, and is always
applied after `presets.toml`.

## How options are combined

![xtask options combination](xtask.drawio.svg)

Options are layered from lowest to highest precedence:

1. shared `[[defaults]]`
2. user `[[defaults]]`
3. shared named preset (`-p`)
4. user named preset (`-p`)
5. explicit CLI flags

CLI flags always win over presets.

## Build artifacts

Everything is placed under cargo's target directory (`core/build-xtask/` by
default), referred to here as `build/`.

### Folder layout

```text
build/
├── <target-triple>/            # hardware only; omitted for emulator
│   └── <profile>/              # debug | debug-opt | release
│       ├── firmware            # raw ELF from cargo
│       ├── firmware.bin        # objcopy output (unsigned)
│       ├── firmware.ubin       # split-bank firmware (STM32F4)
│       ├── firmware.map        # linker map
│       └── firmware.cc.json    # compile_commands for this package
└── artifacts/
    ├── <MODEL_ID>/             # collected, renamed artifacts (see below)
    ├── latest -> <MODEL_ID>    # symlink to most recently built model
    └── pub/                    # versioned, publishable binaries
```

The cargo profile directory is `build/debug` for emulator debug builds,
`build/<triple>/debug-opt` for hardware debug builds, and
`build/<triple>/release` for release builds.

### `artifacts/<MODEL_ID>/`

After a build, xtask copies the relevant outputs here with stable names so
flashing and combining don't depend on the profile path. Files use the
project's artifact name, with `-emu` appended for emulator builds:

- `<name>.elf` — the ELF (hardware); `<name>` (no extension) for emulator.
- `<name>.bin` — signed raw binary (hardware, non-dependency builds only).
- `<name>.map` — linker map (hardware only).
- `<name>.cc.json` — compile_commands; for `firmware`, the merged
  secmon+kernel+firmware commands.

Dependency builds (kernel, secmon when built as part of firmware) collect the
ELF, map and compile_commands but **not** the `.bin`. `xtask combine` writes
`combined-<project>.bin` here.

A combined image pads the gaps between its sections with `0x00`, with one
exception: a region the **boot chain erases on first boot** is padded with
`0xFF`, the erased state. The bootloader erases the UCB region
(`boot_ucb_erase`), so padding it with anything else would make the device stop
matching the image it was flashed from the moment it boots, and a factory line
that verifies by reading flash back would fail. Padded erased, the erase is a
no-op and the image stays byte-identical. Models whose `memory.ld` declares no
such region are unaffected.

Files are copied only if newer, so rebuilding one project doesn't clobber
others. The `latest` symlink always points at the model directory most recently
built.

### `artifacts/pub/`

Versioned, self-describing binaries intended for distribution or archive. The
filename encodes project, model, version, git revision and dirty state, e.g.
`firmware-T3W1-2.8.1-9e4bbc68.bin` (or `-dirty` when the tree is unclean).
Bitcoin-only firmware adds a `-btconly` infix: `firmware-T3W1-btconly-...`.
`xtask combine` publishes `combined-<project>-...` here too.

Kernel and secmon are **not** published (they are intermediate artifacts
consumed only by the firmware build).

### Where `xtask flash` and `xtask upload` read from

On a model with the legacy image layout, both read the signed binary from the
collected artifacts directory:

- `build/artifacts/<MODEL_ID>/<project>.bin`

So a project must be built before it can be flashed or uploaded. `flash` uses
OpenOCD and the flash start address read from the model's `memory.ld`;
`upload` uses `trezorctl fw update`. Only flashable projects
(boardloader, bootloader, bootloader_ci, firmware, prodtest) can be flashed,
and only `firmware`/`prodtest` can be uploaded.

On a model with the `pq_secure_boot` feature they instead read the release
directory — see below.

`xtask flash <project> --combined` reads the combined image instead:

- `build/artifacts/<MODEL_ID>/combined-<project>.bin`

and writes it at `BOARDLOADER_START`, since a combined image always begins at
the bottom of the boot chain — the project name only says WHICH image, not
where it goes. This is the command that takes a blank device to a working
state, boardloader included. Run `xtask combine <project>` first; the image is
flashed exactly as combined, so everything about its contents was decided
there.

The combinable projects are a **narrower set than the flashable ones**: only
`bootloader`, `bootloader_ci`, `firmware` and `prodtest` can head a combined
image. `boardloader` cannot — it is the bottom of the chain that every combined
image already starts with, so there is nothing for it to head.

```sh
xtask combine prodtest -m t3w1
xtask flash   prodtest -m t3w1 --combined
```

## pq_secure releases

A model with the `pq_secure_boot` feature does not have a self-contained
firmware image. A firmware's authenticity is the fold of its manifest up to the
`firmware_root` that the SIGNED BOOTLOADER HEADER commits to, so a firmware
image only means anything next to a bootloader that names the tree it belongs
to. `xtask build firmware` on such a model therefore produces a signed, folded
SET rather than one binary — and it produces it in the ordinary artifacts
directory, signing each image where the build left it:

```text
build-xtask/artifacts/<MODEL_ID>/
├── bootloader.bin        # the built bootloader, header re-signed over this tree
├── firmware.bin          # signed in place, its Merkle co-path baked in
├── prodtest.bin          # likewise, when prodtest was built
├── trezor-ble*.bin       # the nRF image, if the model has one
├── bundle.json           # the container: what this set holds
└── install.zip           # the same, packed for `trezorctl firmware update -f`
```

`xtask release` is the only command that writes a release area, because a
release is a different thing: several variants that cannot share one build
slot, per-model subtrees, and the publishable containers packed from them:

```text
build-xtask/tree/<MODEL_ID>/          # one subtree per released model
build-xtask/tree/<MODEL_ID>.zip       # that model, portable
build-xtask/tree/release[-devel].zip  # every released model, publishable
```

Keeping those apart matters for a mundane reason: while a build also wrote
`tree/<MODEL_ID>.zip`, cutting a release overwrote the file a previous build
had put there, and "did my build reach the device?" depended on which command
wrote it last.

`release.zip` is what gets **published** (`release-devel.zip` when the release
was signed with development keys, so a devel cut cannot quietly overwrite a
production one), and it carries no model in its name on purpose: a release is
not a per-model thing. One source tag builds every model,
the ceremony signs each model's `modelRoot`, and the whole set ships together.
It holds one self-contained subtree per model, with the cross-model index at the
root:

```text
release.zip
├── bundle.json          # the cross-model index (TRZL-set)
├── T3W1/bundle.json     # that model's own container (TRZL)
├── T3W1/bootloader.bin
├── T3W1/<variant>.bin
└── <MODEL_ID>/...       # one subtree per released model
```

Extracting one subtree gives a working per-model release, so the ordinary reader
handles it unchanged — the set adds a level, not a second format. Members come
from what each model's container *names*, so derived files that accumulate in a
release directory (`bootloader-<variant>.bin`, written when stamping) stay out of
the published artifact. `trezorctl` picks the model the same way it picks the
variant: from what the device reports about itself.

The per-model `<MODEL_ID>.zip` stays, because a single device install has no use
for the other models' payloads — that is what `xtask upload` and the OTA harness
consume.

The per-project `artifacts/<MODEL_ID>/firmware.bin` from such a build is **not
installable**: its manifest is an unfilled template, whose leaf folds to
nothing. `xtask flash` and `xtask upload` know this and use the release.

`xtask build` signs a release over the ONE variant its flags select
(`--btc-only`, `--unsafe-fw` for the custom slot, or the `prodtest` project),
which is what a developer usually wants — a one-leaf tree, so a different
`firmware_root` than a full release. `xtask release` cuts the full tree over
every variant; omitting `-m` cuts one release per pq_secure model, which are
independent since each model's `firmware_root` lives in its own header.

Both currently require `--bootloader-devel`, since only development signing
keys are available locally.

### Which bootloader a release folds

Signing rewrites the boot **header**, not the bootloader **code**, so a release
folds an existing bootloader binary and re-signs its header over the release's
`firmware_root`. `--bootloader` picks which binary:

| value | binary |
| --- | --- |
| `auto` (default) | the one you last built for this model, else the committed one |
| `built` | `build/artifacts/<MODEL_ID>/bootloader.bin`; errors if absent |
| `committed` | `models/<MODEL_ID>/bootloaders/bootloader_<MODEL_ID>[_devel].bin` |

The bootloader is **never built implicitly** — a release builds firmware, and
rebuilding the bootloader as a side effect of `xtask build prodtest` would be a
surprise. Run `xtask build bootloader` when you want a fresh one folded in;
`auto` then picks it up, and the build prints which binary it folded (with its
age, for a built one) because that decides which code the device ends up
running.

`--bootloader` applies to **cutting a release** (`xtask release`) and to
**building firmware or prodtest** on a tree model, since those fold a bootloader
they did not build. It is rejected on `xtask build bootloader`, which *produces*
that binary and has nothing to select, and it does not exist on `flash` or
`upload` — see below.

### One bootloader binary, so "flash" means the last one built

`build/artifacts/<MODEL_ID>/bootloader.bin` is the **canonical** bootloader.
Both commands that produce one write there: `xtask build bootloader` compiles
and signs it, and cutting a release copies its folded, signed bootloader back
over it (only once signed — an unsigned release must not become the flashable
artifact, or the boardloader would reject it and the failure would look like a
broken device). Because signing rewrites only the header, the release's copy is
strictly newer than the build's, never a different build.

`flash` and `upload` therefore read that one file and offer no choice of source.
That is deliberate: when two locations both held a bootloader, `xtask build
bootloader` followed by `xtask flash bootloader` silently flashed the *release's*
copy instead of what had just been built — which, if the release had folded the
committed binary, could even be a monotonic version older.

The firmware follows the same rule, by two different routes. A plain `xtask
build` **signs in place** there — nothing is copied anywhere. `xtask release`
signs in its own release area and then publishes the result into the same
directory: each variant's image into its build slot, plus the release's
`bundle.json` rewritten to describe what was published. Either way `flash`,
`upload` and `combine` **install what is there and sign nothing**: signing a third time would re-cut a
one-variant tree over an image that already folds correctly, discarding a
multi-variant release's proof in the process.

`bundle.json` in the artifacts directory is the token saying those binaries form
an installable **set**. It is written together with them, and `xtask build
bootloader` **removes** it — a freshly built bare bootloader commits to nothing,
while the firmware beside it still folds to the previous root, so the pair no
longer agrees. An install then refuses rather than pairing them:

```text
Error: no installable release in build/artifacts/T3W1 -- those binaries are not
a signed set (a bare `build bootloader` invalidates it). Build or cut one:
             xtask build firmware -m T3W1 --bootloader-devel
```

Two consequences of one directory holding one image per slot. Variants sharing
the `firmware.bin` slot cannot coexist, so **building two variants in a row
leaves the first uninstallable** — build the one you mean to install. And where
a multi-variant release publishes, the **first variant in `ALL_VARIANTS` order
wins** the shared slot, which makes it `universal`; without that the slot kept
whichever was compiled last (custom), and `xtask release` followed by `xtask
flash firmware` would quietly install the unofficial variant.

`tree/` is untouched by all of this, and only `xtask release` writes it: it
holds a *cut* release, a publishable artifact rather than an install source.
`xtask upload` reads the same published set the others do, packing it to
`install.zip` because `trezorctl firmware update -f` takes a file. So does the
OTA harness (`make upload_pq_test`), which therefore exercises exactly what a
real install carries.

Whichever is folded must have been built with the same key selection the
release is signed with. A bootloader built without `--bootloader-devel` trusts
the production founder keys, so folding it into a dev-signed release yields a
device that verifies nothing.

`committed` is what a production release must use: there the founder-signed
bootloader is a released artifact whose exact bytes have to be signed over, and
a local rebuild would be the wrong thing.

### The committed reference set

A third party can build custom firmware without any founder key, because the
CUSTOM variant's Merkle leaf is code-independent: the authenticity fold zeroes
the firmware version and the app entry's `size` and `code_hash`, so any
creator's app folds to the one founder-signed custom slot. What the creator
needs instead is a **reference set** — the signed pieces that slot hangs from.
`xtask release --promote` copies a cut release into the tree as that set:

| what | where it lands |
| --- | --- |
| the cross-model bundle | `models/bundle[_devel].json` |
| each model's signed bootloader | `models/<MODEL_ID>/bootloaders/bootloader_<MODEL_ID>[_devel].bin` |
| the secmon pair | `models/<MODEL_ID>/secmon/secmon[_DEV].bin` and `secmon_api[_DEV].o` |

They are promoted together because a bundle only folds against the bootloader
and secmon it was signed over. The bundle is one file for every model, keyed by
model id, since the models are independent trees — merging is a convenience for
whoever reads the set, not a joint tree. Production and development keys get
separate files so promoting one set cannot touch the other's data.

Two details about the pieces. The signed bootloader *replaces* the committed
one rather than sitting beside it: signing rewrites the header and not the code,
so the next release folds this same binary again. And the secmon travels as a
pair — the kernel links the veneer object and secure-faults if it drifts from
the binary it was built against — so a promote fails outright if only one of
them was built.

`presigned_check` proves a set still hangs together, folding the committed
inputs rather than trusting that they were promoted at the same time:

```sh
python3 -m trezor_core_tools.presigned_check                 # every model, both key sets
python3 -m trezor_core_tools.presigned_check -m T3W1
python3 -m trezor_core_tools.presigned_check --from-release build-xtask/tree/T3W1
```

`--from-release` checks a freshly cut release directory instead of the
committed set, which is what you want *before* promoting. It expects a full
release — the custom slot is the thing being verified, and only `xtask release`
cuts every variant, so a single-variant `xtask build` directory is refused.

### Building custom firmware against it

`--unsafe-fw` on a pq_secure model does not cut a tree. A fresh single-variant
root would be self-consistent and useless — no field device carries it — and it
is impossible with production keys anyway, so a custom build folds into the
committed release instead:

```sh
xtask build firmware -m t3w1 --bootloader-devel --unsafe-fw
```

This needs no key. It builds the custom variant **in the artifacts directory**
like every other build — folding the image where the build left it, copying the
promoted bootloader beside it, staging the committed nRF — and reads the
committed bundle where it lives rather than copying it anywhere. The published
manifest is derived from that committed body, trimmed to the one variant
present. A missing bundle is refused up front, naming the fix: cut and promote
a release first.

The other way this fails is a leaf that does not match the one the bundle
records, and that is reported field by field rather than as a bare hash
mismatch, because the differing field is the thing a creator has to change.

Everything the fold does *not* zero still has to match, and that includes the
**whole secmon entry** — secmon is founder-bound even for custom, only the app
is unbound. So a custom build embeds the *committed* secmon rather than a
freshly built one, and `--bootloader` has no effect here: there is nothing to
choose, since the image folds into a header that was signed elsewhere.

That makes the secmon the field most likely to differ, and it is worth knowing
that the diagnostic was blind to it for a while: it parsed the manifest header
as 20 bytes instead of 48, reading the 32-byte translations root as a word, so
`module_count` came out of the middle of that root as zero and **no entry field
was ever compared**. A secmon mismatch then printed "no field differs, yet the
leaves do not match" — which reads as an impossibility rather than an answer.

The release directory and its zip are rebuilt from scratch each time. A
previous full release's variant binaries left beside a bundle that lists them
would invite installing a stale one, and `xtask upload` installs the zip rather
than the directory, so a leftover zip is worse than a missing one — it is
plausible, and it installs the wrong image.

### Flashing a release

```sh
xtask build firmware -m t3w1 --bootloader-devel
xtask flash firmware -m t3w1
```

Nothing has to be decided at build time: one release installs either over the
wire or with a debugger.

`xtask flash firmware` writes the **bootloader and the firmware together**, in
one OpenOCD run. They are one unit — the bootloader's signed header carries the
`firmware_root` that the firmware folds up to, and rebuilding the firmware
changes that root, so the bootloader already on the device vouches only for the
previous build. There is no useful "flash just the firmware" on a tree model.

The header also carries `firmware_type`, the provisioning marker. It holds a
32-bit hardened codeword rather than a small number, so no single bit flip turns
one variant into another; the `NONE` codeword means the device reads as
*unprovisioned* and boots nothing. An over-the-wire install writes the variant
into it; a debugger install has nobody to do that, so `xtask flash` stamps it
while writing the bootloader. The field is unauthenticated, so this needs no key
and leaves the signature intact — the release itself stays bare. `bundle.json`
records where the field sits and how wide it is (the signer locates it by
probing its own build), the value a bare release carries, and each variant's
value, so no tool duplicates the boot-header layout or the codewords.

### Preparing, signing, assembling

A founder ceremony cannot run inside a build: the key is not there. So cutting a
release is three stages, and `xtask release` performs them in that order rather
than signing each model as it is built:

| stage | keys | what it does |
|---|---|---|
| **prepare** | none | build every model, fill every manifest, fold every tree, seat each boot header in its model tree — and leave the signature region **zero** |
| **sign** | founder | 32 bytes per model out, two hybrid signature pairs per model back |
| **attach** | none | patch those signatures into the prepared artifacts, then pack |

The order matters beyond tidiness: signing model 1 while model 2 has not been
built is not something an airgapped step can do, and `sigmask` is *authenticated*
— inside the digest — so which key slots will sign has to be committed during
prepare, before any leaf exists.

Attaching afterwards is safe because **every signature lands in unauthenticated
space**: the boot header's `slh_signature[]` / `ec_signature[]` sit past
`auth_size`, and a PQ-native co-processor's founder records live in unprotected
TLVs whose *sizes* were reserved before its leaf was computed. No digest moves,
so nothing prepare folded is invalidated. It is the same property that lets
`firmware_type` be stamped into a signed bootloader without a key.

The prepared container **is the signing request** — each model records the
`modelRoot` its header commits to — so there is no second request format to keep
in step with the release.

`xtask release` requires one of `--bootloader-devel` or `--production`, because
the two select key sets on **different axes** and exactly one pairing is
dangerous. `--bootloader-devel` picks the founder pool the boot chain trusts
(`root_keys.h`, on `BOOTLOADER_DEVEL`); `--production` picks the keys that sign
translations and coin definitions (the `dev_keys` cargo feature). With neither, a
release carries production founder keys and *development* data keys — it enforces
secure boot, so it looks shippable, yet it accepts translations and definitions
signed with private halves checked into this repository. The requirement is
explicit because that is the case you get by typing nothing.

```sh
# development: prepared, then signed with dev keys and assembled, in one command
xtask release -m t3w1 --bootloader-devel

# production: stops after prepare, unsigned, waiting for the ceremony
xtask release -m t3w1 --production
#   -> release-unsigned.zip
# ... ceremony returns a signature set ...
python tools/trezor_core_tools/firmware_pq_attach.py \
    --release build-xtask/tree --signatures signatures.json
```

`firmware_pq_devsign.py` is the ceremony's stand-in for development: it signs a
prepared release with the development keys and writes the signature set that
`firmware_pq_attach.py` consumes. It is the only step that touches a key, which
is what makes it the one a real release replaces.

A standalone `xtask build firmware` still signs inline — a developer wants one
command and holds the development keys.

### The release container

`bundle.json` describes the release: which variants it holds, what each folds
to, which file is the bootloader, and any co-processor payloads. It opens with
`format` (`TRZL`) and `format_version`, and every reader **rejects a version it
does not know** rather than guessing — a release cut by an older tool is refused
by version, not diagnosed one absent field at a time.

It carries **no signature and needs none**. The boot-header signature is the
trust root, and the device pins the stamped `firmware_type` to the authenticated
manifest variant, so a tampered container is a fail-closed DoS and never a
forgery. Read everything in it as routing — which file is which — not authority.
Two consequences worth knowing:

- A variant is identified by its own `variant` name, taken from the codeword in
  its folded manifest. Readers do not recover identity by stripping `.bin` off a
  filename, which would make the writer's naming a claim about what an image is.
- Co-processor entries are addressed by their `(kind, index)` slot — the same
  tuple bound into the co-processor's Merkle leaf. It says which payload belongs
  in which slot; every verifier still takes kind and index from its *own* build
  configuration, never from here.

The archive is written deterministically (fixed member timestamps and order), so
identical inputs give identical bytes and the container can be digested.

`--variant` picks which variant to flash, needed only when the release holds
more than one and the project does not name it by itself:

```sh
xtask flash prodtest -m t3w1                  # prodtest IS the variant
xtask flash firmware -m t3w1 --variant custom  # a full release needs to be told
```

Flashing the bootloader on its own leaves it **bare** — the legitimate state of
a fresh device, which then takes its firmware over the wire — unless
`--variant` asks for it to be provisioned:

```sh
xtask flash bootloader -m t3w1                    # bare
xtask flash bootloader -m t3w1 --variant btc-only  # provisioned, for testing
```

### Combining a release

`xtask combine` builds the single image a factory line flashes, and takes its
bootloader and firmware from the release on the same terms as `xtask flash` —
same `--variant`, same stamp, same bootloader-is-bare-alone rule:

```sh
xtask combine prodtest -m t3w1
```

Flash it with the same project name plus `--combined`, which writes the whole
chain in one go from the boardloader address — the command that puts a blank
device into a working state:

```sh
xtask flash prodtest -m t3w1 --combined
```

Everything about the image's contents was settled by `xtask combine`, so
`--variant` belongs there and is refused here.

## Tips and common pitfalls

- Omit `--board` to use the model's default board.
- Emulator builds require the selected board to declare an `emulator_header`.
- `--storage-insecure-testing-mode` and `--production` are mutually exclusive.
- An option absent from a project's `[build-options]` is silently ignored by
  that project.
- An unknown preset name, or a preset with no matching `when` fragment, is an
  error.
- Run `xtask build --help` for the full list of flags.
