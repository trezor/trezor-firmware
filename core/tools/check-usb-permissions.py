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
cmd("ls -l /sys/bus/usb/devices")
cmd("ls -vl `find /sys/bus/usb/devices/usb*/ -name disable`")
cmd(
    'for F in `find /sys/bus/usb/devices/usb*/ -name disable | sort -V`; do echo -n "$F "; cat $F; done'
)
cmd(
    'for F in /sys/bus/usb/devices/usb*; do echo -n "$F -> "; CTRL=$(readlink -f $F/..); echo $CTRL; od -An -tx1 -N8 "$CTRL/config"; cat $CTRL/power/runtime_status; readlink $CTRL/driver; echo; done'
)
cmd("lsusb --tree -v")
cmd("uhubctl --version")
cmd("ldd `which uhubctl`")
cmd("strace --color=never -fZ uhubctl")
