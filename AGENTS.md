# AGENTS.md

Compact guide for AI coding assistants working in this repo. Verify commands against the
Makefiles if in doubt; this file only captures what is non-obvious.

## Environment setup

- This is a monorepo. Top-level dirs: `core` (Trezor Core firmware, MicroPython + Rust + C),
  `legacy` (Trezor One, C), `crypto` (C crypto lib), `storage` (NORCOW, C), `python` (trezorlib + `trezorctl`),
  `common` (coin defs + protobuf), `rust` (standalone Rust crates), `tests` (integration suite), `tools`, `vendor` (submodules).
- **All system deps come from `nix-shell`, all Python deps from `uv`.** Every command below assumes both are
  active. Check with `echo $IN_NIX_SHELL $VIRTUAL_ENV`; if either is empty (or `xtask`/`pyright`/`ruff` is not
  found), set up from the repo root:
  ```sh
  git submodule update --init --recursive --force
  nix-shell                    # system deps (Rust nightly, SDL2, clang, protoc, ...)
  uv sync                      # Python deps into .venv (re-run when uv.lock changes)
  source .venv/bin/activate
  ```
  For a one-off command without an interactive shell: `nix-shell --run "uv run <command>"` (this is what CI does).
- Extra deps: `nix-shell --arg fullDeps true` (upgrade/monero tests: bitcoind, old emulators),
  `--arg devTools true` (OpenOCD, gdb, arm-gcc), `--arg pythonTest true` (Python interpreters for `tox`).

## Builds (core)

- Builds go through `xtask` (a venv entry point wrapping `cargo xtask` in `core/embed/`; it compiles itself on
  first use). `xtask build <project> -m <model>` — **`-m` is required**. Models: `T2T1`, `T2B1`, `T3B1`,
  `T3T1`, `T3T2`, `T3W1`, discovery boards `D001`–`D003` (case-insensitive). The core Makefile defaults to
  `TREZOR_MODEL=T3W1`. Projects: `firmware`, `bootloader`, `boardloader`, `prodtest`, `secmon`, ...
  Artifacts land in `core/build/artifacts/<MODEL>/`, symlinked as `artifacts/latest`.
- Emulator: `xtask build firmware --emulator -m <model> [-p <preset>]` (~1 min). Embedded: drop `--emulator`.
- **Build presets** (`-p <name>`, defined in `core/embed/xtask/presets.toml`, docs in `docs/core/build/xtask.md`).
  CLI flags override presets (e.g. `-p test --frozen false`). Personal presets go in git-ignored
  `core/embed/xtask/user-presets.toml`.
  - No preset: non-frozen (Python read from `core/src`, edits need no rebuild), **no debuglink**.
  - `-p test`: frozen + debuglink + no animations — the build CI uses for device/UI/click tests.
  - `-p test-live`: like `test` but non-frozen. **Best default for agents**: works for unit tests *and*
    device/UI tests, and Python edits are picked up on emulator restart without rebuilding.
  - `-p dev`: non-frozen + ASAN.
  - **Debuglink comes only from `--debug-link`** (set by the `test*` presets); `--pyopt false` alone does not
    enable it. Without debuglink, pytest fails with `RuntimeError: No debuggable device found`.
- Other flags: `--btc-only`, `--production`, `--bootloader-devel` (exclusive with `--production`), `--asan`,
  `--disable-tropic`, `--n1w1`, `--debug`. See `xtask build --help`.
- Legacy (Trezor One) builds are separate: see `docs/legacy/index.md`.

## Running the emulator

- `./core/emu.py` runs the last built emulator (`artifacts/latest`). Agents have no display: **always pass
  `-h` (`--headless`)**, otherwise it dies with `SDL_Init error`. `-h` also disables animations.
- Simplest and safest — run a command against a throwaway emulator that is torn down afterwards
  (exit code is propagated):
  `./core/emu.py -h -t -P <port> -q -c pytest tests/device_tests -k test_msg_ping`
  (`-t` temporary profile, `-P` UDP base port, `-q` silences emulator logs, `-c` runs the rest as a command).
- Long-running emulator (to iterate with several pytest/`trezorctl` calls):
  ```sh
  setsid nohup ./core/emu.py -h -P <port> -p <name> >/tmp/emu-<name>.log 2>&1 </dev/null &
  # wait for "Emulator ready" in the log, then:
  export TREZOR_PATH=udp:127.0.0.1:<port>
  pytest tests/device_tests -k <name>; trezorctl get-features
  kill "$(cat ~/.trezoremu/<name>/trezor.pid)"   # stop it
  ```
  The profile (`~/.trezoremu/<name>/`) holds flash, `trezor.pid` and the Tropic model log; `-e` erases it on start.
  Plain `nohup ... &` gets killed with the spawning shell. Stop the emulator by killing the **`trezor.pid`
  process** — `emu.py` then shuts down cleanly. Killing the `emu.py` process itself orphans `firmware-emu`
  and `model_server`.
- T3W1 (Safe 7) needs the Tropic01 model server; `emu.py` starts and stops it automatically (TCP 28992).
  `Fatal: tropic_pin_unmask_kek failed` on startup = stale state between flash and model server; restart
  with `-e` (or `-t`).

## Tests

- **Core unit tests** (MicroPython, run inside `firmware-emu`, not pytest): `make -C core test`, single file:
  `make -C core test TESTOPTS=test_apps.bitcoin.address.py` (files live in `core/tests/`; ~2 min for all).
  - Needs a **non-frozen** build (no preset, `-p test-live`, or `make -C core build_unix`). A frozen build fails
    with a bare `OSError: 19` / `Task #1 terminated`.
  - On **T3W1**, start the Tropic model first (unit tests don't go through `emu.py`), otherwise
    `Fatal: Failed to initialize Tropic driver`:
    `model_server tcp -c tests/tropic_model/firmware_config/current.yml &` — stop it afterwards and never run it
    while an `emu.py` T3W1 emulator is up (same port).
- **Device tests** (pytest against an emulator built with debuglink): `make -C core test_emu` (starts its own
  temporary emulator via `emu.py -c`), or `pytest tests/device_tests ...` against a running one.
  - Select: `-k <name>`, `-m <marker>` (markers in `tests/REGISTERED_MARKERS`), or a file path. Via make:
    `TESTOPTS="-x -k test_msg_ping" make -C core test_emu`.
  - Tests adapt to the running emulator's model. To test another model, rebuild with `-m <model>`.
  - Tests are randomized (pytest-random-order); the seed is printed in the header. `PYTEST_TIMEOUT=<sec>`
    sets the per-test timeout.
- **UI tests** compare screenshot hashes in `tests/ui_tests/fixtures.json`.
  - Full suite: `make -C core test_emu_ui` (check), `make -C core test_emu_ui_record` (re-record).
  - Single test: `pytest tests/device_tests -k <name> --ui=test`. **Do not add `--ui-check-missing` to a subset
    run**: it reports every test that did not run as missing and fails. Worse, with `--ui=record` it *removes*
    them from `fixtures.json`. To re-record a subset, use `--ui=record` alone. Same reason: never
    `tests/update_fixtures.py local --remove-missing` after a subset run.
  - On failure, check `tests/ui_tests/screens/<test>/actual/` and `tests/ui_tests/reports/test/` (`index.html`,
    `diff/`); `./tests/show_results.py` opens the report.
- Click tests: `make -C core test_emu_click[_ui]`. Persistence tests (spawn their own emulators):
  `make -C core test_emu_persistence[_ui]`. Prodtest: `make -C core build_prodtest_emu test_emu_prodtest`.
- Upgrade tests: `nix-shell --arg fullDeps true`, `tests/download_emulators.sh <model>`, then
  `make -C core test_emu_upgrade` (limit with `TREZOR_UPGRADE_TEST=T2T1,T3W1`).
- Python client: `make -C python test` (quick, current interpreter); full matrix as CI:
  `nix-shell --arg pythonTest true --run "unset LD_LIBRARY_PATH && cd python && uv run tox"`.
- Rust: `make -C core test_rust` (embedded crates), `make -C core clippy`, `make -C rust check` (standalone crates).
- Crypto: `make -C crypto` then e.g. `crypto/tests/test_check`. Storage: `make -C storage/tests build tests_all`.
- Coverage: `make -C core coverage` (builds a frozen emulator if needed). CI threshold is 85%.

## Parallel agents / worktrees

Multiple emulators coexist only if each has its own port block and profile. Each emulator uses
**7 consecutive UDP ports** from its base (default 21324): wire, debuglink, FIDO2, VCP, BLE ×2, (tropic).

- Always pass a unique `-P <port>` (above 30000, spaced ≥ 8 apart) and `-t` or `-p <name>`; never use the
  default port 21324 or the default profile `/var/tmp`.
- Always export `TREZOR_PATH=udp:127.0.0.1:<port>` for pytest/`trezorctl` against a running emulator —
  otherwise they probe 21324 and may attach to **another agent's emulator**. (`emu.py -c` sets it for you.)
- Isolate make targets with `TREZOR_UDP_PORT=<port> make -C core test_emu*`; set
  `TREZOR_PROFILE_DIR=<unique dir>` for `make -C core test` (it binds no ports but shares `/var/tmp`).
- Stop only your own emulator (`kill "$(cat <profile>/trezor.pid)"`). **Never** `pkill -f firmware-emu` or
  `pkill -f model_server` — that kills every agent's processes.
- Machine-wide singletons, one at a time:
  - The Tropic model on TCP 28992, i.e. any **T3W1** emulator (`emu.py` hardcodes the port) and T3W1 unit tests.
    Use other models (T3T1, T2T1) in parallel worktrees, or take turns.
  - Runs that spawn their own emulators with `--control-emulators` (`*_multicore`, `test_emu_persistence*`,
    `test_emu_upgrade`) and `test_emu_prodtest` — their ports are fixed (base 20000), so concurrent runs collide.

## Style, types, lint

- `make style` applies all formatters (ruff fix + format, clang-format for C/proto, rustfmt, changelog,
  translation JSON sort) and then runs the type/lint checks.
- `make style_check` is the full CI gate (~1 min): pyright, flake8, ruff, pylint, rustfmt, clang-format,
  changelog, translations, yamllint, editorconfig, docs summary. Run it before committing.
- `make pystyle_quick_check` — fast pre-commit (ruff format check + import order).
- **Python formatter/linter is ruff** (plus flake8 and pylint). **Typechecker is pyright, not mypy**:
  `make typecheck` (repo) and `make -C core typecheck` (firmware sources).
- Python files subject to linting are selected by `tools/style.py.include` / `tools/style.py.exclude`.

## Generated files

- `make gen` regenerates all generated files; `make gen_check` (CI gate) verifies they are up to date.
- **Never hand-edit or resolve merge conflicts in generated files.** Run `make gen` and commit the result,
  e.g. right after a rebase/merge.
- Generated artifacts include: `core/mocks/generated/*` (from C module comments), every `*.py`/`*.rs` next to a
  `*.mako` template (coin/token lists, translated strings), protobuf classes in `core/src/trezor/messages` and
  `python/src/trezorlib/messages` (from `common/protob/*.proto`), plus FIDO icons, vendor headers, bootloader
  hashes, linker scripts, ...
- Translations: after editing `core/translations/en.json` run `make -C core templates` (sorts keys, regenerates
  translation data and the Rust string table `core/embed/rust/src/translations/generated/translated_string.rs`),
  verify with `make -C core translations_check`. Without it the new string is not compiled into the firmware.

## Conventions

- **Conventional Commits**: `type(scope): subject`, scope one of
  `common|core|crypto|legacy|python|storage|tools|vendor` (optional but preferred), e.g. `feat(core): ...`.
  Subject under 50 chars; details as `-` bullets in the body. See `COMMITS.md`; hooks in `docs/git/hooks/`.
- **Changelog entries** for user-facing changes (features, fixes, behavior changes): a one-line file
  `<component>/.changelog.d/<issue>.<type>` ending with a period, types
  `added|changed|deprecated|removed|fixed|security|incompatible`; model-specific entries start with `[T2T1]`
  etc.; use `noissue` if there is no issue number. Refactors, tests and internal changes instead put
  `[no changelog]` in the commit message (conventionally as the last line). See `docs/misc/changelog.md`.
- Fixup commits are blocked from merging (CI `block-fixup`).
- New pytest markers must be registered in `tests/REGISTERED_MARKERS`. Scope tests to models with
  `@pytest.mark.models(...)`; shortcuts (`MODEL_SHORTCUTS` in `tests/conftest.py`): `core`, `legacy`, `t1`,
  `t2`/`tt`, `safe`, `safe3`, `safe5`, `delizia` (T3T1), `eckhart` (T3W1). Layout names: `bolt` (T2T1),
  `caesar` (Safe 3), `delizia` (Safe 5), `eckhart` (Safe 7).

## Reference docs

- Build/emulator/embedded: `docs/core/build/`. Emulator features: `docs/core/emulator/`. Test types:
  `docs/tests/`. Misc: `docs/misc/` (`generated-files.md`, `changelog.md`, `contributing.md`, `git-hooks.md`).
