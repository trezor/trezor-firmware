#!/usr/bin/env python3
"""Start the prodtest emulator, run a command, then stop it.

Usage:

    ./prodtest_emu.py pytest ../tests/prodtest_tests
    TREZOR_MODEL=t3w1 ./prodtest_emu.py pytest ../tests/prodtest_tests
"""

import argparse
import os
import shutil
import signal
import subprocess
import sys

from trezorlib.prodtest.prodtest_emulator import get_prodtest_emulator

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("-m", "--model", default=os.environ.get("TREZOR_MODEL"))
args, remaining = parser.parse_known_args()

if not args.model:
    print("No model specified. Use -m <model> or set TREZOR_MODEL.", file=sys.stderr)
    sys.exit(1)

emulator = get_prodtest_emulator(model=args.model)

try:
    with emulator:
        emulator.start()
        process = subprocess.Popen(remaining)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        returncode = process.wait()
finally:
    shutil.rmtree(emulator.profile_dir, ignore_errors=True)

sys.exit(returncode)
