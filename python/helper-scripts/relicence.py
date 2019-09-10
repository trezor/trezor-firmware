#!/usr/bin/env python3

LICENSE_NOTICE = """\
# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

SHEBANG_HEADER = """\
#!/usr/bin/env python3

"""

EXCLUDE_FILES = ["src/trezorlib/__init__.py", "src/trezorlib/_ed25519.py"]
EXCLUDE_DIRS = ["src/trezorlib/messages"]


def one_file(fp):
    lines = list(fp)
    new = lines[:]
    shebang_header = False

    if new[0].startswith("#!"):
        shebang_header = True
        new.pop(0)
        if not new[0].strip():
            new.pop(0)

    while new and new[0][0] == "#":
        new.pop(0)

    while new and new[0].strip() == "":
        new.pop(0)

    new.insert(0, LICENSE_NOTICE)
    if shebang_header:
        new.insert(0, SHEBANG_HEADER)
    data = "".join(new)

    fp.seek(0)
    fp.write(data)
    fp.truncate()


import glob
import os
import sys


def main(paths):
    for path in paths:
        for fn in glob.glob(f"{path}/**/*.py", recursive=True):
            if any(exclude in fn for exclude in EXCLUDE_DIRS):
                continue
            if fn in EXCLUDE_FILES:
                continue
            statinfo = os.stat(fn)
            if statinfo.st_size == 0:
                continue
            with open(fn, "r+") as fp:
                one_file(fp)


if __name__ == "__main__":
    main(sys.argv[1:])
