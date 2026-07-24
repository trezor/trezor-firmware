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
- Emulator (unix port): `xtask build firmware --emulator -m <model>`.
  - `--pyopt false` is **required for any test/fixture work** — it enables debuglink (without it the build is
    "production" and tests cannot connect: `DebugLinkNotFound`). It also adds `--disable-animation --dbg-console vcp`.
  - `--frozen` freezes Python into the binary (faster test startup, but must rebuild on Python changes).
    These two combine: `xtask build firmware --emulator --frozen --pyopt false -m <model>` is the recommended
    test build (fast + debuglink). Without `--frozen`, Python sources are read from disk (picks up edits without rebuild).
  - Run with `./core/emu.py` (use `-a` to disable animations for faster tests).
- Embedded: `xtask build firmware -m <model>` (also `boardloader`, `bootloader`, `prodtest`, `secmon`).
- Common `xtask build` flags (the Makefile exposes these as env vars; prefer the flags directly):
  `--btc-only`, `--pyopt false` (debuglink/debug build; also adds `--disable-animation --dbg-console vcp`),
  `--production`, `--asan`, `--bootloader-devel`, `--disable-tropic true|false`, `--n4w1`, `--debug true`.
  `--production` and `--bootloader-devel` are mutually exclusive. `--pyopt false` is orthogonal to `--frozen`
  and `--production`; it is required whenever you intend to drive the emulator via debuglink (tests/fixtures).

## Tests

- Core unit tests (run on the emulator binary directly, not pytest): `make -C core test`
  → runs `core/tests/run_tests.sh` against `firmware-emu`. Requires a built emulator first
  (`xtask build firmware --emulator --pyopt false -m <model>`, or `make -C core build_unix`).
  Run a single unit test: `cd core/tests && ../build-xtask/artifacts/latest/firmware-emu test_apps.bitcoin.address.py`.
- Device/integration tests (pytest against a running emulator): `make -C core test_emu`.
  The make target auto-launches the emulator; from a shell run `pytest tests/device_tests` after starting `./core/emu.py`.
  - Single test: `pytest tests/device_tests -k <name>` or `-m <marker>` (markers in `tests/REGISTERED_MARKERS`).
  - `TESTOPTS="-x -v -k test_msg_backup_device.py" make -C core test_emu` for Makefile-driven runs.
  - `INTERACT=1 pytest ...` to press buttons yourself. `PYTEST_TIMEOUT=<sec>` per-test timeout.
  - Tests are randomized via pytest-random-order; the seed is printed in the header.
- UI tests (screenshot fixtures): `make -C core test_emu_ui` (check) / `test_emu_ui_record` (update fixtures in `tests/ui_tests`).
  `--ui-check-missing` ensures all fixtures are exercised.
  - **Recording a subset is dangerous with `--ui-check-missing`:** in `--ui=record` mode that flag doubles as
    `remove_missing=True` and prunes every fixture not in the current run from `fixtures.json`. To re-record only
    a single test, run `--ui=record` *without* `--ui-check-missing` (only the tests that ran get updated), or
    manually patch the specific hash entry in `tests/ui_tests/fixtures.json`. Do **not** run
    `tests/update_fixtures.py local --remove-missing` after a subset run for the same reason.
- Click tests: `make -C core test_emu_click[_ui]`. Persistence tests: `test_emu_persistence[_ui]`.
- Upgrade tests: require `nix-shell --arg fullDeps true` and `tests/download_emulators.sh <model>`,
  then `make -C core test_emu_upgrade`. Limit with `TREZOR_UPGRADE_TEST=T2T1,T3W1`.
- T3W1 (Safe 7) tests need the Tropic model server running in the background:
  `model_server tcp -c tests/tropic_model/config.yml &` (CI starts this automatically for T3W1).
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
