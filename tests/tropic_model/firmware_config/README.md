# Tropic model firmware configs

This directory holds the Tropic model configurations used when running firmware
(as opposed to prodtest) against the model, most notably by the upgrade tests.

- `current.yml` — the configuration matching the current firmware on `main`.
- `X_Y_Z.yml` — a snapshot of an older configuration, used by firmware releases
  up to and including version X.Y.Z.

For a given firmware version, the tests pick the oldest `X_Y_Z.yml` with
X.Y.Z >= the firmware version, falling back to `current.yml`
(see `_get_tropic_model_configfile` in `tests/upgrade_tests/conftest.py`).

## When changing `current.yml`

Check whether any firmware has been released since the previous change to
`current.yml`. If so, copy the previous content of `current.yml` to
`X_Y_Z.yml`, where X.Y.Z is the latest release made before your change (the
copy covers all releases since the previous change), and make sure upgrade
tests pass. A CI bot (`.github/workflows/bot-tropic-emulator.yml`) posts this
reminder on pull requests touching `current.yml`.
