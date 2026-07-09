# AGENTS.md

Compact guide for AI coding assistants working in this repo. Verify commands against the
Makefiles if in doubt; this file only captures what is non-obvious.

## Environment setup

- This is a monorepo. Top-level dirs and ownership: `core` (Trezor Core firmware, MicroPython + Rust + C),
  `legacy` (Trezor One, C), `crypto` (C crypto lib), `storage` (NORCOW, C), `python` (trezorlib + `trezorctl`),
  `common` (coin defs + protobuf), `rust` (standalone Rust crates), `tests` (integration suite), `tools`, `vendor` (submodules).
- All commands below assume you are inside `nix-shell` with the venv activated. If `xtask` or `pyright` is
  not found, run `nix-shell` then `source .venv/bin/activate`. For upgrade/monero tests you need
  `nix-shell --arg fullDeps true` (pulls bitcoind, old SDL2 emulators, monero tests).
- Embedded dev tools (OpenOCD, gdb, arm-gcc): `nix-shell --arg devTools true`.

## Builds (core)

- Builds go through a Rust `xtask` binary wrapped by Makefiles. Model is selected via `-m <model>`
  (default `T3W1`). Supported: `T2T1`, `T2B1`, `T3B1`, `T3T1`, `T3W1`, plus discovery boards `D001`/`D002`.
- `xtask` is a venv entry point (wraps `cargo xtask` run from `core/embed/`); just activate the venv and it's
  on `PATH`. It auto-builds its Rust binary on first use. `make -C core` with no target only prints help.
- Emulator (unix port): `xtask build firmware --emulator -m <model>`, optionally with a preset (below).
  Run with `./core/emu.py` (use `-a` to disable animations for faster tests).
- Embedded: `xtask build firmware -m <model>` (also `boardloader`, `bootloader`, `prodtest`, `secmon`).
- **Build presets** (`-p <name>`) live in `core/embed/xtask/presets.toml` (full docs: `docs/core/build/xtask.md`).
  Layers, lowest to highest precedence: shared `[[defaults]]` → named preset → CLI flags (CLI always wins,
  e.g. `-p test --frozen false`). Personal overrides go in git-ignored `xtask/user-presets.toml`.
  - No preset (emulator): non-frozen — Python sources are read from disk (edits need no rebuild) — but
    **no debuglink**.
  - `-p test`: `frozen` + `pyopt false` + `debug-link` + `disable-animation` — the build for device/UI/click
    tests and fixtures.
  - `-p test-live`: like `test` but non-frozen — debuglink with Python read from disk; use while iterating
    on Python code.
  - `-p dev`: non-frozen + ASAN development build.
  - **Debuglink comes only from `debug-link`** (the `test*` presets or `--debug-link`); `pyopt false` alone
    does NOT enable it (it only adds debug/overlay features). Without debuglink, tests cannot connect
    (`DebugLinkNotFound`).
- Common `xtask build` flags: `--btc-only`, `--production`, `--asan`, `--bootloader-devel`,
  `--disable-tropic true|false`, `--n1w1`, `--debug true`, `--frozen`, `--pyopt false`, `--debug-link`.
  `--production` and `--bootloader-devel` are mutually exclusive.

## Tests

- Core unit tests (run on the emulator binary directly, not pytest): `make -C core test`
  → runs `core/tests/run_tests.sh` against `firmware-emu`. Requires a **non-frozen** emulator build
  (`xtask build firmware --emulator -m <model>` with no preset, `-p test-live`, or `make -C core build_unix`).
  Frozen builds don't mount the host FS, so running a test file from disk fails with a bare `OSError: 19`
  and `Task #1 terminated` (no traceback) — unit tests and device tests need **different emulator builds**.
  Run a single unit test: `cd core/tests && ./run_tests.sh test_apps.bitcoin.address.py`. Do not invoke
  `firmware-emu` directly — the script sets `MICROPYPATH=.:../src`, `-X heapsize=2M` and `SDL_VIDEODRIVER=dummy`,
  without which the test fails with `ImportError: no module named 'trezor'`.
- Device/integration tests (pytest against a running emulator): `make -C core test_emu`.
  Requires an emulator built **with debuglink**: `-p test` (frozen) or `-p test-live` (live Python sources).
  Without it, `emu.py` logs `DebugLink not found: udp:...` and pytest fails with
  `RuntimeError: No debuggable device found`. Same requirement for UI/click/persistence tests below.
  The make target auto-launches the emulator; from a shell run `pytest tests/device_tests` after starting `./core/emu.py`.
  - Single test: `pytest tests/device_tests -k <name>` or `-m <marker>` (markers in `tests/REGISTERED_MARKERS`).
  - Tests auto-adapt to the model of the running emulator. To test another model, rebuild and restart the
    emulator with `-m <model>` (e.g. `-m T2T1`); `make -C core` targets take `TREZOR_MODEL=<model>` (default `T3W1`).
  - The emulator stays in the foreground — use a second terminal, or detach it with
    `setsid nohup ./core/emu.py -a >/tmp/emu.log 2>&1 </dev/null &` (plain `nohup ... &` gets killed with
    the spawning shell's process group). Stop it with `pkill -f "[f]irmware-emu"` (the bracket avoids
    matching your own shell's command line).
  - `TESTOPTS="-x -v -k test_msg_backup_device.py" make -C core test_emu` for Makefile-driven runs.
  - `INTERACT=1 pytest ...` to press buttons yourself. `PYTEST_TIMEOUT=<sec>` per-test timeout.
  - Tests are randomized via pytest-random-order; the seed is printed in the header.
- UI tests (screenshot fixtures): `make -C core test_emu_ui` (check) / `test_emu_ui_record` (update fixtures in `tests/ui_tests`).
  `--ui-check-missing` ensures all fixtures are exercised.
  - Run/check a single UI test against a running emulator:
    `pytest tests/device_tests -k <name> --ui=test --ui-check-missing`.
  - When a UI test fails, the actual screenshots land in `tests/ui_tests/screens/<test_name>/actual/` and HTML
    comparison reports in `tests/ui_tests/reports/test/` (`all_screens.html`, `diff/`) — check these first when
    debugging a UI failure.
  - **Recording a subset is dangerous with `--ui-check-missing`:** in `--ui=record` mode that flag doubles as
    `remove_missing=True` and prunes every fixture not in the current run from `fixtures.json`. To re-record only
    a single test, run `--ui=record` *without* `--ui-check-missing` (only the tests that ran get updated), or
    manually patch the specific hash entry in `tests/ui_tests/fixtures.json`. Do **not** run
    `tests/update_fixtures.py local --remove-missing` after a subset run for the same reason.
- Click tests: `make -C core test_emu_click[_ui]`. Persistence tests: `test_emu_persistence[_ui]`.
- Upgrade tests: require `nix-shell --arg fullDeps true` and `tests/download_emulators.sh <model>`,
  then `make -C core test_emu_upgrade`. Limit with `TREZOR_UPGRADE_TEST=T2T1,T3W1`.
- T3W1 (Safe 7) needs the Tropic model server, but `core/emu.py` starts it automatically when the built
  emulator has tropic support — no manual step needed; **do not run another `model_server` in parallel**
  (they fight over the same TCP port). Start it manually
  (`model_server tcp -c tests/tropic_model/config.yml &`) only if you launch the `firmware-emu` binary directly
  instead of via `emu.py` (CI runs it as a separate service).
  - `Fatal: tropic_pin_unmask_kek failed at storage.c` on startup = stale pairing state between the
    emulator's flash image and a restarted model server. Fix: kill both, wipe the profile
    (`rm -f /var/tmp/trezor.{flash,sdcard,pid,port}` — or `$TREZOR_PROFILE_DIR/trezor.*` if set), restart.
- Python client (`python/`): `cd python && uv run tox` (CI: `unset LD_LIBRARY_PATH` first inside nix-shell).
- Rust crates: `make -C rust check` (clippy + test + audit). Core embedded rust tests: `make -C core -f Makefile.scons test_rust`
  and `make -C core clippy`. `trezor-client` tests need a running emulator.
- Crypto lib: `make -C crypto` then run `crypto/tests/test_check` etc.
- Storage: `make -C storage/tests build && make -C storage/tests tests_all`.
- Coverage threshold on CI is 85%. Generate locally: `make -C core coverage` (needs a frozen build with `.i` files).

## Style, types, lint

- `make style_check` is the full gate (flake8, isort, black, pylint, pyright, rustfmt, clang-format for C/proto,
  yamllint, editorconfig-checker, changelog, translations, docs-summary). Apply fixes with `make style`.
- Use `make pystyle_quick_check` for a fast pre-commit (isort + black only).
- **Typechecker is pyright, not mypy.** `make typecheck` (root + `core`) runs `tools/pyright_tool.py`.
  `make -C core typecheck` is a prerequisite of the full style check.
- Python file selection for linting is governed by `tools/style.py.include` / `tools/style.py.exclude`, not the whole tree.
- Black runs with `--fast` by default (`BLACK_FAST=1`); CI's full check uses `BLACK_FAST=0`.

## Generated files

- `make gen` regenerates all generated files; `make gen_check` (CI gate) verifies they are up to date.
- **Never hand-edit or resolve merge conflicts in generated files.** Run `make gen` and commit the result.
  After rebasing/merging branches, immediately run `make gen`.
- Generated artifacts include:
  - `core/mocks/generated/*` — mock Python stubs from C module comments (`make mocks`).
  - `*.py` next to any `*.py.mako` — coin/token lists (`networks.py`, `tokens.py`, `coininfo.py`, `nem_mosaics.py`)
    rendered from `common/defs` (`make templates`).
  - Protobuf message classes in `core/src/trezor/messages` and `python/src/trezorlib/messages` from `common/protob/*.proto` (`make protobuf`).
  - FIDO icons, vendor header, Solana templates, bootloader hashes, linker scripts, tropic config, HSM keys, prodtest error codes.
- Translations: `make -C core translations` / `translations_check` (sorts keys + regenerates blobs + checks merkle root).
  - Editing a string value in `core/translations/en.json` also requires regenerating the Rust string table
    `core/embed/rust/src/translations/generated/translated_string.rs` (a mako template) via `make -C core templates`,
    otherwise the change is not embedded in the firmware.

## Conventions

- **Conventional Commits** with scope required by the suggested hook: `type(scope): subject` where scope is one of
  `common|core|crypto|legacy|python|storage|tools|vendor` (e.g. `feat(core): ...`). See `COMMITS.md`.
  Subject line under 50 chars; commit body can contain additional detail as `-` bullet points.
- **Changelog entries are mandatory** for non-trivial, user-facing changes only (new features, bug fixes, behavior
  changes, breaking changes). Refactors, test improvements, internal cleanup, and other changes not observable by
  end users should use `[no changelog]` (at the very end of the commit message) to opt out. Add `<component>/.changelog.d/<issue>.<type>`
  (types: `added|changed|deprecated|removed|fixed|security|incompatible`).
  Model-specific entries start with `[T2T1]` etc. Release branches (`release/YY.MM`) have generated `CHANGELOG.md` — edit directly.
- Fixup commits are blocked from merging (CI `block-fixup`).
- New pytest markers must be registered in `tests/REGISTERED_MARKERS`. Use `@pytest.mark.models(...)` to scope tests
  to models. Shortcuts (defined in `tests/conftest.py` `MODEL_SHORTCUTS`): `core`, `legacy`, `t1`, `t2`/`tt`,
  `safe`, `safe3`, `safe5` (model families), `delizia` (T3T1), `eckhart` (T3W1). The latter two are UI system names;
  other layout names: `caesar` (safe3), `bolt` (model T / TT).
- Generated `CHANGELOG.unreleased` files exist per component; `tools/changelog.py` generates final sections at release.

## Reference docs

- Build/emulator/embedded: `docs/core/build/`. Test types: `docs/tests/`. Misc gotchas: `docs/misc/`
  (`generated-files.md`, `changelog.md`, `contributing.md`, `git-hooks.md`).
- `docs/git/hooks/` contains copyable git hooks: `cp docs/git/hooks/* .git/hooks/`.
