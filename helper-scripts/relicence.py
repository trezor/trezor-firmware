#!/usr/bin/env python3

LICENSE_NOTICE = """\
# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

"""

EXCLUDE_FILES = ["trezorlib/__init__.py", "trezorlib/_ed25519.py"]


def one_file(fp):
    lines = list(fp)
    new = lines[:]
    while new and new[0][0] == "#":
        new.pop(0)

    while new and new[0].strip() == "":
        new.pop(0)

    data = "".join([LICENSE_NOTICE] + new)

    fp.seek(0)
    fp.write(data)
    fp.truncate()


import glob
import os

for fn in glob.glob("trezorlib/**/*.py", recursive=True):
    if fn in EXCLUDE_FILES:
        continue
    statinfo = os.stat(fn)
    if statinfo.st_size == 0:
        continue
    with open(fn, "r+") as fp:
        one_file(fp)
