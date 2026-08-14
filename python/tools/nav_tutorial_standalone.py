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

"""Run the Safe 3 navigation tutorial using a STOCK trezorlib install.

Hand this file to someone who has plain `trezorctl` / `trezorlib` from PyPI and
a Safe 3 flashed with the navigation-prototype debug firmware. It declares the
two debug-only protobuf messages itself, so nothing needs to be installed from
the feature branch.

    pip install trezor          # if they do not have it already
    python3 nav_tutorial_standalone.py

The raw interaction log is printed and saved next to the script. Send the .log
file back; it decodes with `trezorlib.nav_telemetry` on the branch.
"""

from __future__ import annotations

import datetime
import os
import sys

from trezorlib import mapping, protobuf
from trezorlib.client import get_default_client

# Wire ids from common/protob/messages.proto on the navigation-prototype branch.
SHOW_NAV_TUTORIAL = 9105
NAV_TUTORIAL_RESULT = 9106


class ShowNavTutorial(protobuf.MessageType):
    MESSAGE_WIRE_TYPE = SHOW_NAV_TUTORIAL
    FIELDS: dict = {}


class NavTutorialResult(protobuf.MessageType):
    MESSAGE_WIRE_TYPE = NAV_TUTORIAL_RESULT
    FIELDS = {
        1: protobuf.Field("status", "string", repeated=False, required=False),
        2: protobuf.Field("log", "string", repeated=False, required=False),
    }

    def __init__(self, status: str | None = None, log: str | None = None) -> None:
        self.status = status
        self.log = log


def main() -> int:
    # Teach a stock trezorlib about the two debug messages.
    mapping.DEFAULT_MAPPING.register(ShowNavTutorial)
    mapping.DEFAULT_MAPPING.register(NavTutorialResult)

    client = get_default_client("nav-tutorial")
    session = client.get_session(passphrase=None)  # no seed / PIN needed

    print("Follow the tutorial on the device...")
    with session:
        result = session.call(ShowNavTutorial(), expect=NavTutorialResult)

    print(f"Tutorial {result.status}.")
    if not result.log:
        print("No interaction log was returned.")
        return 1

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    name = f"nav-tutorial-{stamp}.log"
    with open(name, "w") as f:
        f.write(result.log)
    print(f"Interaction log saved to {name}")
    print(f"Full path: {os.path.abspath(name)}")
    print("Please send that file back.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
