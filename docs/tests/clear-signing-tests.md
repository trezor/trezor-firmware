# Clear-signing tests

Nightly UI tests of Ethereum clear signing (ERC-7730). They sign the test transactions of
the [clear-signing registry](https://github.com/ethereum/clear-signing-erc7730-registry)
on the emulator, with the display formats of the unsigned dev definitions of
[trezor/definitions](https://github.com/trezor/definitions). Only mainnet, only English,
on all core models.

They are separate from the [device tests](device-tests.md): they live in
`tests/clear_signing_tests/`, run in their own workflow
(`.github/workflows/core-clear-signing.yml`), and do not use the device tests' UI fixtures.
Each run compares its screens with those of the **last nightly run**, so it shows what
changed since then, and its own screens are what the next run compares with.

## Inputs

The test cases and the definitions must match, so both come from one trezor/definitions
commit: the one built by the last run of its "[Deploy] unsigned dev firmware
definitions" workflow (from any branch).

- **Definitions:** that deploy, `s3://dev.firmware.sldev.cz/unsigned/v2/definitions/`
  (from the internal network also `https://dev.firmware.sldev.cz/unsigned/v2/definitions/`).
- **Test cases:** the `registry/*/testsv2/calldata-*.tests.json` files of the registry
  commit that this trezor/definitions commit pins as a submodule.

So the tests change exactly when someone deploys the unsigned dev definitions.
`tests/clear_signing_tests/nightly.py resolve-inputs` finds the commits. It fails when the
last deploy did not succeed, since a failed deploy may have left the bucket half-synced.
`nightly.py check-definitions` fails when the deployed definitions are older than the
minimum that the firmware accepts
(`common/defs/ethereum/released-definitions-timestamp.json`). In both cases, re-run the
deploy.

## What fails

Each registry case with a chain ID 1 transaction is one test. A case is skipped when the
dev definitions have no display format for its contract and function (the definitions
converter dropped it, or it is not deployed there), or when its calldata is longer than
the firmware clear-signs (6144 bytes).

A test fails when:

- signing fails,
- its screens differ from those of the last nightly run, or the test did not run then
  (`UI_FAILED`, `UI_MISSING`),
- a test of the last nightly run no longer runs, e.g. because a display format disappeared.

Blind signing (the firmware shows the `confirm_data` screen although the dev
definitions have a display format) is not a failure. It is recorded like clear signing,
and listed in the summary. A case that changes from one to the other fails on its
screens.

Since the next run compares with this one, a UI change fails only the one run that
brings it. In the UI report, a new test shows *missing* in place of the previous screens,
and a test that no longer runs (under "Removed tests") shows its previous screens next
to *missing* ones.

The registry's `expected` texts (intent, labels and values) are also looked up on the
screens, but a text that is not found is only reported: the firmware formats some values
differently.

## Baseline

`tests/clear_signing_tests/nightly.py fetch-baseline` writes the fixtures that a run
compares with. For each model, they are the screens of the last finished scheduled run
on `main` that has them: the `fixtures.results.json` of its UI report on
`data.trezor.io`. The UI report of these tests uploads the screens of every test, not
only of the passing ones, so that the next report can show the differences.

A model that none of the last 10 nightly runs has screens for (e.g. before the first
run) falls back to the base fixtures in `tests/clear_signing_tests/fixtures.json`, recorded
locally (see below). Re-record them only when that fallback matters, e.g. after a long
outage of the nightly runs.

## Results

The summary of the workflow run has, per model, the counts, links to the
[UI report](ui-tests.md) and to the run it was compared with, and lists the skipped
cases, the failures, and the expected texts that were not found. The UI report is the
same as that of the device tests: `index.html` lists the failed, new and passed tests,
each failed test shows its screens next to those of the last run, with a diff, and
`differing_screens.html` has all the changed screens on one page. The per-case results
(screens' texts, ButtonRequests) are in the `clear-signing-results-<model>` artifacts.

## Running locally

From the internal network, the dev definitions can be used by their URL. Check out the
registry at the commit from `resolve_inputs.py`:

```sh
tests/clear_signing_tests/nightly.py resolve-inputs   # prints registry_sha
git clone --filter=blob:none --sparse https://github.com/ethereum/clear-signing-erc7730-registry /tmp/registry
git -C /tmp/registry sparse-checkout set --no-cone '/registry/*/testsv2/'
git -C /tmp/registry checkout <registry_sha>

export TREZOR_CLEAR_SIGNING_REGISTRY=/tmp/registry
export TREZOR_CLEAR_SIGNING_DEFINITIONS=https://dev.firmware.sldev.cz/unsigned/v2/definitions/
```

Then, with an emulator built with debuglink (e.g. `xtask build firmware --emulator -m T3W1 -p test`):

```sh
# a few cases against a temporary emulator
TREZOR_UI_FIXTURES=tests/clear_signing_tests/fixtures.json \
  ./core/emu.py -h -t -q -c pytest tests/clear_signing_tests -k 1inch --ui=test --lang=en
# all cases, like CI
make -C core test_emu_clear_signing_ui
# then open the report, with the diffs
TREZOR_UI_FIXTURES=tests/clear_signing_tests/fixtures.json ./tests/show_results.py
```

Always set `TREZOR_UI_FIXTURES` when running these tests with `--ui`, and when opening
their report with `show_results.py`, otherwise their screens go to
`tests/ui_tests/fixtures.json`. The make targets do it, and the end of the pytest output
prints the `show_results.py` command with it.

To compare with the last nightly run instead of the base fixtures:

```sh
tests/clear_signing_tests/nightly.py fetch-baseline -o /tmp/clear-signing-fixtures.json
make -C core test_emu_clear_signing_ui CLEAR_SIGNING_FIXTURES=/tmp/clear-signing-fixtures.json
TREZOR_UI_FIXTURES=/tmp/clear-signing-fixtures.json ./tests/show_results.py
```

To re-record the base fixtures, record each model in turn (each run replaces only the
screens of its own model):

```sh
for MODEL in T2T1 T3B1 T3T1 T3W1; do
  xtask build firmware --emulator -m $MODEL -p test
  make -C core test_emu_clear_signing_ui_record
done
```
