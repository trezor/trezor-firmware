#!/usr/bin/env python3

import subprocess
from pathlib import Path


def cmd(command: str) -> None:
    try:
        command = f"{command} 2>&1"
        print(f"COMMAND: {command}")
        completed = subprocess.run(command, shell=True, capture_output=True, text=True)
        print(completed.stdout)
        if completed.returncode != 0:
            print(f"RETURNED: {completed.returncode}")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
    print("")


cmd("uname -a")
cmd("uptime")
cmd("id")
dirs = " ".join(str(d) for d in Path("/dev/bus/usb").parents)
cmd(f"ls -ld /dev/bus/usb/* {dirs}")
cmd("ls -l /dev/bus/usb/*")
cmd("ls -vl `find /sys/bus/usb/devices/usb*/ -name disable`")
cmd(
    'for F in `find /sys/bus/usb/devices/usb*/ -name disable | sort -V`; do echo -n "$F "; cat $F; done'
)
cmd('for P in /sys/bus/usb/devices/usb*/*/usb*-port*; do printf \'%-32s %-10s %s\n\' "${p##*/}" "$(cat $P/connect_type)" "$(cat $P/physical_location/panel 2>/dev/null)"; done')
cmd("lspci -v")
cmd("lsusb --tree -v")
cmd("uhubctl --version")
cmd("ldd `which uhubctl`")
cmd("strace --color=never -fZ uhubctl")
