#!/usr/bin/env python3

# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

"""Run one Safe 3 navigation-tutorial session and save the interaction log.

Meant for moderated usability testing: one invocation per participant, no CLI
flags to remember. Requires a debug (PYOPT=0) firmware, because the tutorial is
debug-only.

    ./nav_study.py p07

writes `nav-p07-<timestamp>.{log,json,txt}` into the output directory: the raw
encoded log for re-analysis, the decoded statistics as JSON for aggregating
across participants, and the human-readable report.

To re-analyse saved logs later without a device:

    ./nav_study.py --report nav-p07-*.log

To decode a transcript captured from the device's serial console instead
(`screen /dev/cu.usbmodem* 115200`, or any terminal - the device streams every
event live, so this survives an interrupted session):

    ./nav_study.py --serial session.txt
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

from trezorlib import nav_telemetry


def save(session: nav_telemetry.Session, base: Path, raw_log: str | None) -> None:
    if raw_log is not None:
        base.with_suffix(".log").write_text(raw_log)
    base.with_suffix(".json").write_text(json.dumps(session.to_dict(), indent=2))
    base.with_suffix(".txt").write_text(nav_telemetry.format_report(session))
    print(nav_telemetry.format_report(session))
    print()
    print(f"Saved {base.name}.{{log,json,txt}}")


def run_session(participant: str, outdir: Path, device: str | None) -> int:
    from trezorlib.client import get_default_client
    from trezorlib.nav_tutorial import show_nav_tutorial

    client = get_default_client("nav-study", device)
    # A seedless session is enough - the tutorial needs no seed, PIN or
    # passphrase. This is what `trezorctl debug nav-tutorial` uses too.
    session = client.get_session(passphrase=None)

    print(f"Participant {participant}: hand the device over, tutorial is starting.")
    result = show_nav_tutorial(session)

    if not result.log:
        print(f"Tutorial {result.status}, but no interaction log was returned.")
        return 1

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = outdir / f"nav-{participant}-{stamp}"
    save(nav_telemetry.decode(result.log, status=result.status), base, result.log)
    return 0


def report_logs(paths: list[Path]) -> int:
    for path in paths:
        print(f"=== {path.name} ===")
        session = nav_telemetry.decode(path.read_text())
        print(nav_telemetry.format_report(session))
        print()
    return 0


def report_serial(paths: list[Path]) -> int:
    found = 0
    for path in paths:
        sessions = nav_telemetry.decode_serial(path.read_text())
        if not sessions:
            print(f"{path.name}: no '{nav_telemetry.SERIAL_TAG}' lines found.")
            continue
        for index, session in enumerate(sessions, start=1):
            found += 1
            print(f"=== {path.name} (session {index} of {len(sessions)}) ===")
            print(nav_telemetry.format_report(session))
            print()
    return 0 if found else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "participant",
        nargs="?",
        help="participant id, used in the output filenames",
    )
    parser.add_argument(
        "-o",
        "--outdir",
        type=Path,
        default=Path("."),
        help="where to write the results (default: current directory)",
    )
    parser.add_argument(
        "-d",
        "--device",
        help="device path, e.g. webusb:001:3 (default: first attached device)",
    )
    parser.add_argument(
        "--report",
        nargs="+",
        type=Path,
        metavar="LOG",
        help="re-print the report for saved .log files, without a device",
    )
    parser.add_argument(
        "--serial",
        nargs="+",
        type=Path,
        metavar="TRANSCRIPT",
        help="decode a captured serial-console transcript instead",
    )
    args = parser.parse_args()

    if args.report:
        return report_logs(args.report)
    if args.serial:
        return report_serial(args.serial)
    if not args.participant:
        parser.error("give a participant id, or use --report / --serial")

    args.outdir.mkdir(parents=True, exist_ok=True)
    return run_session(args.participant, args.outdir, args.device)


if __name__ == "__main__":
    sys.exit(main())
