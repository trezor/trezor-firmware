#!/usr/bin/env python3
"""Check whether a UI change defeats the RP2350 display-bus implant's screen recogniser.

The implant (found on a tampered Safe 5, T3T1) sniffs the display bus, thresholds every
frame (ink = 6-bit green > 30), splits it into text bands (>= 5 empty rows apart, max 8)
and band 0 into pieces (>= 5 px gaps, max 16), and CRC-32s each cropped bitmap. A CRC
equal to one of TRIGGERS starts seed / passphrase capture. This script records the
emulator screens of the tests that show those screens, runs the same recogniser on them
and reports which triggers still match compared with a baseline from the unchanged UI.

USAGE
  python3 tools/implant_check/implant_check.py <worktree> <tag> [options] [-- pytest args]

  <worktree>       trezor-firmware checkout containing the UI change to check. The
                   emulator-only patches next to this script are applied there if missing
                   (revert later with: git -C <worktree> apply -R <patch>).
  <tag>            name of the run; output goes to --out (default ./implant_check_<tag>/):
                   screens/, build.log, pytest_*.log, summary.json, result.txt

  --port N         emulator UDP base port (default 31464); use a unique one per parallel run
  --skip-build     reuse the emulator already built in <worktree>
  --tests P [P..]  test paths relative to <worktree>/tests (default: backup, recovery and
                   passphrase device tests + all click tests, ~15 min)
  --baseline F     baseline summary (default: baseline_T3T1_en.json next to this script)
  --save-baseline  write summary.json as a new baseline instead of comparing; run it on the
                   unchanged UI after a firmware update that moves the baseline
  --out DIR        output directory
  -- ARGS          passed to pytest, e.g. -- --lang de

EXAMPLES
  # check a UI change in ../tf-kerning
  python3 tools/implant_check/implant_check.py ../tf-kerning kerning
  # re-run only the recovery tests on the existing build
  python3 tools/implant_check/implant_check.py ../tf-kerning kerning --skip-build \\
      --tests device_tests/reset_recovery

EXIT CODE
  0  no trigger matches and every trigger seen in the baseline was exercised -> mitigated
  1  at least one trigger still matches -> not mitigated
  2  nothing checked (setup or build failed, no screens recorded)
  3  no trigger matches, but some trigger was not exercised -> add the tests that show it

Run inside nix-shell with the repo venv active (needs Pillow and the emulator toolchain).
Only the T3T1 emulator is supported (the implant targets Safe 5). Limits: only settled
debuglink screens are checked (not intermediate frames), coverage is limited to the tests
run, and bus-level changes (command order, timing) cannot be tested in the emulator.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
import shutil
import subprocess
import sys
import zlib
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
DEFAULT_BASELINE = HERE / "baseline_T3T1_en.json"
# emu_dma2d_model: pixel-exact DMA2D blending, so emulator pixels equal the device's bus pixels
# emu_long_paths: the emulator's 256-byte screenshot path buffers truncate long test-dir
#   paths, so every frame overwrites one file and a test keeps only its last screen
PATCHES = [HERE / "emu_dma2d_model.patch", HERE / "emu_long_paths.patch"]
DEFAULT_TESTS = [
    "device_tests/reset_recovery",
    "device_tests/test_msg_backup_device.py",
    "device_tests/test_repeated_backup.py",
    "device_tests/test_session_id_and_passphrase.py",
    "device_tests/test_passphrase_slip39_advanced.py",
    "device_tests/test_passphrase_slip39_basic.py",
    "click_tests",
]

# "Wallet backup" + "Recovery share #1..#16" titles (fw v2.7.0 - v2.12.1)
SHARES = [
    0xBAB713D0, 0x69BFBB58, 0xDF01B55F, 0x0FDB30A5, 0x81C1ECAC, 0xEE774518,
    0x1A647CF8, 0x42DA0520, 0x24A559C7, 0xECDB184F, 0x60B9FD9D, 0x6F6D9FF9,
    0xFE61EE3E, 0x22EA63D7, 0x280A4486, 0x675095F0,
]  # fmt: skip
TRIGGERS = {
    0xA44796D7: "T1  Wallet backup (backup words)",
    0x5F305451: "T2  The word is repeated",
    **{c: f"T{3 + i:<2} Recovery share #{1 + i}" for i, c in enumerate(SHARES)},
    0xF0358906: "T19 Confirm passphrase (host passphrase)",
    0xD75EDBA9: "T20 Word N of M (recovery words)",
    0xB43A7487: "T21 Success (recovery commit)",
    0x6B158B42: "T22 keyboard confirm icon (device passphrase)",
    0xBEFD9413: "T23 keyboard commit, unidentified",
}


class SetupError(Exception):
    pass


# --- recogniser ------------------------------------------------------------------------


def _runs(ink: list[bool], gap: int, maxn: int) -> list[tuple[int, int]]:
    """Split a 1-D ink profile into [start, end) runs separated by >= gap empty entries."""
    out, start, empty = [], None, 0
    for i, v in enumerate(ink):
        if v:
            if start is None:
                start = i
            elif empty >= gap:
                out.append((start, i - empty))
                start = i
            empty = 0
        elif start is not None:
            empty += 1
    if start is not None:
        out.append((start, len(ink) - empty))
    return out[:maxn]


def _crop_crc(rows: list[bytes]) -> int | None:
    cols = [x for x in range(len(rows[0])) if any(r[x] for r in rows)]
    ys = [i for i, r in enumerate(rows) if any(r)]
    if not cols:
        return None
    return zlib.crc32(
        b"".join(rows[y][cols[0] : cols[-1] + 1] for y in range(ys[0], ys[-1] + 1))
    )


def screen_triggers(png: Path) -> list[int] | None:
    """Trigger CRCs found on one screen (as a band or a band-0 piece); None if not 240x240.

    Matching any piece is more permissive than the implant's layout checks, so 0 is a safe 0.
    """
    im = Image.open(png).convert("RGB")
    if im.size != (240, 240):
        return None
    green = im.getchannel("G").tobytes()
    g = [
        bytes(0xFF if (v >> 2) > 30 else 0 for v in green[y * 240 : (y + 1) * 240])
        for y in range(240)
    ]
    crcs = []
    for i, (y0, y1) in enumerate(_runs([any(r) for r in g], gap=5, maxn=8)):
        rows = g[y0:y1]
        crcs.append(_crop_crc(rows))
        if i == 0:
            for xa, xb in _runs(
                [any(r[x] for r in rows) for x in range(240)], gap=5, maxn=16
            ):
                crcs.append(_crop_crc([r[xa:xb] for r in rows]))
    return sorted({c for c in crcs if c in TRIGGERS})


def summarize(screens: Path) -> dict:
    """Per-test screen counts and per-trigger hit counts for every screens/<test>/*.png."""
    pngs = sorted(screens.glob("*/*.png"))
    tests, hits = Counter(), {}
    with ProcessPoolExecutor() as ex:
        for png, found in zip(pngs, ex.map(screen_triggers, pngs, chunksize=32)):
            if found is None:
                continue
            # dir name is <MODEL>_<lang>-<test id>
            test = re.sub(r"^[A-Z0-9]+_[a-z]{2}-", "", png.parent.name)
            tests[test] += 1
            for c in found:
                hits.setdefault(f"0x{c:08x}", Counter())[test] += 1
    return {"screens": sum(tests.values()), "tests": dict(tests), "hits": hits}


def compare(base: dict, cand: dict) -> int:
    """Print the per-trigger table and return the exit code (see module docstring)."""
    # a test that recorded far fewer screens than in the baseline did not really run (e.g. the
    # emulator got stuck after an earlier failure); it must not count as coverage
    short = {t for t, n in cand["tests"].items() if n < 0.5 * base["tests"].get(t, 0)}
    if short:
        print(
            f"WARNING: {len(short)} test(s) recorded < 50% of their baseline screens, not counted:"
        )
        for t in sorted(short)[:5]:
            print(f"  {cand['tests'][t]:4}/{base['tests'][t]:<4} {t}")
    ran = set(cand["tests"]) - short
    print(f"screens: baseline {base['screens']}, candidate {cand['screens']}")
    print(f"{'trigger':50} {'base':>6} {'cand':>6}")
    fired, uncovered = [], []
    for c, name in TRIGGERS.items():
        bt, ct = base["hits"].get(f"0x{c:08x}", {}), cand["hits"].get(f"0x{c:08x}", {})
        nb, nc = sum(bt.values()), sum(ct.values())
        if not nb and not nc:
            continue
        if nc:
            fired.append((name, sorted(ct)[:3]))
            flag = "<-- STILL FIRES"
        elif ran & set(bt):
            flag = "mitigated"
        else:
            uncovered.append(name)
            flag = "NOT COVERED (none of the baseline tests showing it ran)"
        print(f"{name:50} {nb:6} {nc:6}  {flag}")
    if not cand["screens"]:
        print("\nRESULT: no candidate screens, nothing was checked")
        return 2
    if fired:
        print("\nexample tests still firing:")
        for name, tests in fired:
            print(f"  {name[:3]} {', '.join(tests)}")
        print(f"\nRESULT: {len(fired)} trigger(s) still match")
        return 1
    print("\nRESULT: no trigger matches on any candidate screen")
    if uncovered:
        print(
            f"WARNING: {len(uncovered)} trigger(s) not exercised; add the tests that show them"
        )
        return 3
    return 0


# --- emulator run ----------------------------------------------------------------------


def apply_patches(wt: Path) -> bool:
    """Apply missing emulator patches; return True if anything was applied."""
    applied = False
    for p in PATCHES:
        git = ["git", "-C", str(wt), "apply"]
        if (
            subprocess.run(
                git + ["--check", "-R", str(p)], capture_output=True
            ).returncode
            == 0
        ):
            continue  # already applied
        r = subprocess.run(git + [str(p)], capture_output=True, text=True)
        if r.returncode:
            raise SetupError(f"{p.name} does not apply:\n{r.stderr}")
        print(f"applied {p.name} to {wt} (revert: git -C {wt} apply -R {p})")
        applied = True
    return applied


def build(wt: Path, log: Path) -> None:
    print(f"building T3T1 emulator (-p test-live), log: {log} ...")
    cmd = [
        "cargo",
        "xtask",
        "build",
        "firmware",
        "--emulator",
        "-m",
        "T3T1",
        "-p",
        "test-live",
    ]
    with log.open("w") as f:
        r = subprocess.run(
            cmd, cwd=wt / "core/embed", stdout=f, stderr=subprocess.STDOUT
        )
    if r.returncode:
        raise SetupError(f"build failed, see {log}")


def clear_screens(screens: Path) -> None:
    """Remove recordings from earlier runs, keeping the tracked .gitignore."""
    for p in screens.iterdir() if screens.exists() else []:
        if p.name == ".gitignore":
            continue
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p)
        else:
            p.unlink()


def collect(screens: Path, out: Path) -> None:
    for actual in screens.glob("*/actual"):
        if any(actual.glob("*.png")):
            shutil.copytree(actual, out / actual.parent.name)
    clear_screens(screens)


def run_tests(
    wt: Path, tests: list[str], port: int, extra: list[str], log: Path
) -> None:
    cmd = [
        "./core/emu.py",
        "-h",
        "-t",
        "-P",
        str(port),
        "-q",
        "-c",
        "pytest",
        *tests,
        "--ui=test",
        *extra,
    ]
    with log.open("w") as f:
        subprocess.run(cmd, cwd=wt, stdout=f, stderr=subprocess.STDOUT)
    # a nonzero pytest exit is normal here: --ui=test fails every screen that differs from
    # the fixtures. Show the summary line so real test failures are visible.
    summary = [
        ln
        for ln in log.read_text(errors="replace").splitlines()
        if " in " in ln and "==" in ln
    ]
    print(
        "  " + (summary[-1].strip("= ") if summary else f"no pytest summary, see {log}")
    )


def main() -> int:
    if isinstance(sys.stdout, io.TextIOWrapper):
        # keep progress visible when the output is piped or logged
        sys.stdout.reconfigure(line_buffering=True)
    argv = sys.argv[1:]
    extra = argv[argv.index("--") + 1 :] if "--" in argv else []
    argv = argv[: argv.index("--")] if "--" in argv else argv
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("worktree", type=Path)
    ap.add_argument("tag")
    ap.add_argument("--port", type=int, default=31464)
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--tests", nargs="+", default=DEFAULT_TESTS)
    ap.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    ap.add_argument("--save-baseline", action="store_true")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)

    wt = a.worktree.resolve()
    out = (a.out or Path(f"implant_check_{a.tag}")).resolve()
    shots = out / "screens"
    ui_screens = wt / "tests/ui_tests/screens"
    shutil.rmtree(shots, ignore_errors=True)
    shots.mkdir(parents=True)

    try:
        if apply_patches(wt) and a.skip_build:
            raise SetupError(
                "patches were just applied: drop --skip-build so the emulator is rebuilt"
            )
        if not a.skip_build:
            build(wt, out / "build.log")
    except SetupError as e:
        print(e)
        return 2

    tests = [str(wt / "tests" / t) for t in a.tests]
    # device and click tests in separate emulator sessions (a hung click test cannot stall the rest)
    groups = {
        "device": [t for t in tests if "click_tests" not in t],
        "click": [t for t in tests if "click_tests" in t],
    }
    clear_screens(ui_screens)
    for name, group in groups.items():
        if group:
            print(
                f"running {name} tests on port {a.port} (UI mismatches vs fixtures are expected) ..."
            )
            run_tests(wt, group, a.port, extra, out / f"pytest_{name}.log")
            collect(ui_screens, shots)

    cand = summarize(shots)
    (out / "summary.json").write_text(json.dumps(cand, indent=1, sort_keys=True))
    print(
        f"recognised {cand['screens']} screens from {len(cand['tests'])} tests in {shots}"
    )
    if a.save_baseline:
        a.baseline.write_text(json.dumps(cand, indent=1, sort_keys=True) + "\n")
        print(f"baseline written to {a.baseline}")
        return 0

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = compare(json.loads(a.baseline.read_text()), cand)
    print(buf.getvalue(), end="")
    (out / "result.txt").write_text(buf.getvalue() + f"exit code {rc}\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
