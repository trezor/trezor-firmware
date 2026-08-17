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
  device via OpenOCD.
- `xtask flash-erase [section] -m <model>` — erase a flash section (`all`,
  `boardloader`, `bootloader`, `firmware`, `storage`).
- `xtask reset -m <model>` — reset the connected device.
- `xtask upload <project> -m <model>` — upload firmware/prodtest to a running
  device.
- `xtask combine <project> -m <model>` — combine the dependency chain (e.g.
  secmon + kernel + firmware) into a single flashable binary.

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
- `--n4w1` — enable N4W1 support.
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

Both `xtask flash` and `xtask upload` read the signed binary from the
collected artifacts directory:

- `build/artifacts/<MODEL_ID>/<project>.bin`

So a project must be built before it can be flashed or uploaded. `flash` uses
OpenOCD and the flash start address read from the model's `memory.ld`;
`upload` uses `trezorctl fw update`. Only flashable projects
(boardloader, bootloader, bootloader_ci, firmware, prodtest) can be flashed,
and only `firmware`/`prodtest` can be uploaded.

## Tips and common pitfalls

- Omit `--board` to use the model's default board.
- Emulator builds require the selected board to declare an `emulator_header`.
- `--storage-insecure-testing-mode` and `--production` are mutually exclusive.
- An option absent from a project's `[build-options]` is silently ignored by
  that project.
- An unknown preset name, or a preset with no matching `when` fragment, is an
  error.
- Run `xtask build --help` for the full list of flags.
