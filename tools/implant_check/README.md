# Checking a UI change against the RP2350 implant

The RP2350 implant recognises Trezor Safe 5 screens by CRC-32 checksums of their pixels: it
thresholds each frame on the green channel, cuts it into text bands and title pieces, and compares
their CRC-32s with a fixed list of trigger screens (the list is in `TRIGGERS` in the script; details
are in the internal analysis report). `implant_check.py` (branch `bleska/implant_check`) tells you whether a UI change, such as different kerning, colour, layout or wording, stops those
checksums from matching. It runs the relevant tests in the emulator, applies the implant's recogniser
to every recorded screen and compares the result with the unchanged English UI.

---

## 1. Prerequisites (once)

1. **Development environment.** Set it up as described in `AGENTS.md`: submodules, `nix-shell`,
   `uv sync`, then activate the venv. Every command below runs inside that shell.

2. **Get the tool.** Check out the branch in its own worktree:
   ```sh
   git worktree add ../tf-implant-tool bleska/implant_check
   ```
   The tool is a single script, `../tf-implant-tool/tools/implant_check/implant_check.py`. Next to
   it are two emulator patches and the baseline. Run `implant_check.py --help` for the full usage.

3. **A worktree with the UI change to test.** Create a separate checkout for the change. Don't use
   your main checkout, because the tool patches the emulator in that worktree:
   ```sh
   git worktree add ../tf-kerning <your-branch>
   git -C ../tf-kerning submodule update --init --recursive
   ```

4. **A free port.** Each run needs 7 consecutive UDP ports. The default base port is 31464; give
   parallel runs base ports at least 8 apart. Only T3T1 (Safe 5) is supported.

## 2. Running the check

```sh
python3 ../tf-implant-tool/tools/implant_check/implant_check.py ../tf-kerning kerning
```

What happens:

| Step | Time |
|---|---|
| Apply `emu_dma2d_model.patch` and `emu_long_paths.patch` to the worktree if they are missing | – |
| Build the T3T1 emulator with `-p test-live` | ~1–3 min |
| Run the backup, recovery and passphrase device tests | ~2 min |
| Run all click tests | ~12 min |
| Recognise the screens and compare them with the baseline | seconds |

Results go to `./implant_check_kerning/`: the recorded `screens/`, `build.log`, `pytest_*.log`,
`summary.json` and `result.txt`.

**Patches:**
- `emu_dma2d_model.patch` makes the emulator blend pixels like the device's DMA2D hardware. Without
  it the checksums never match and every change looks like a mitigation.
- `emu_long_paths.patch` fixes screenshot paths being truncated in long worktree paths. Without it
  each test keeps only its last screen.
- Both patches are for testing only. Don't commit them with your change. To revert one:
  `git -C ../tf-kerning apply -R <patch>`.

**Useful options:**
- `--skip-build` reuses the existing build, for example after changing only the test selection.
- `--tests device_tests/reset_recovery click_tests/test_passphrase_bde.py` runs a faster subset.
- `-- --lang de` passes arguments to pytest, here to check another language.

**Expected noise:**
- Pytest reports many `ui_failed` tests. This is expected, because the screens differ from the
  fixtures.
- About 4 click tests time out. They still record their screens.
- The tool prints each pytest summary line, so real crashes are visible.

## 3. Reading the result

`result.txt` (also printed at the end), shortened:

```
screens: baseline 33036, candidate 31890
trigger                                              base   cand
T1  Wallet backup (backup words)                      387      0  mitigated
T20 Word N of M (recovery words)                     3229     36  <-- STILL FIRES
T22 keyboard confirm icon (device passphrase)        4234   4199  <-- STILL FIRES

example tests still firing:
  T20 test_recovery_bip39, ...

RESULT: 2 trigger(s) still match
exit code 1
```

`base` and `cand` count the screens on which the trigger matched, before and after the change.
The numbers above are an illustration, not a real run.

| Exit code | Meaning | What to do |
|---|---|---|
| **0** | No trigger matches, and every trigger was exercised | the change defeats the recogniser in the emulator; confirm on hardware |
| **1** | At least one trigger still matches | the change is not sufficient for that trigger; the example tests show where |
| **2** | Nothing was checked | read `build.log` / `pytest_*.log` |
| **3** | No matches, but some trigger was never shown | add the tests that show it (see `NOT COVERED`); with a subset this is expected |

A test that recorded less than half of its baseline screens is listed and **not** counted as coverage.
This stops a crashed run from passing as "mitigated".

## 4. Updating the baseline

The baseline (`baseline_T3T1_en.json`) records which tests show which trigger in the unchanged
English UI. If the firmware on `main` changes the affected screens for other reasons, regenerate the
baseline on an unchanged checkout:

```sh
python3 .../implant_check.py ../tf-main main --save-baseline
```

Then commit the updated JSON.

## 5. Limits

- Only the final screen of each debuglink step is checked. Animation frames are not, although the
  implant sees them. Disable animations or check them on hardware if the change relies on them.
- Coverage is limited to the tests that run. A screen that no test shows is not checked.
- Matching is more permissive than the implant: any title piece counts. So "0" is a safe 0, but a
  "STILL FIRES" may in rare cases not fire on the device.
- Bus-level changes (command order such as RASET-first, timing) cannot be tested in the emulator.
- **The final proof is the hardware A/B test on the affected device.**
