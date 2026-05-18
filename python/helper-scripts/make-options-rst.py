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

import argparse
from pathlib import Path
from typing import TextIO

import click

from trezorlib.cli import trezorctl

DELIMITER_STR = "### ALL CONTENT BELOW IS GENERATED"
OPTIONS_RST = Path(__file__).resolve().parent / "../docs/OPTIONS.rst"

parser = argparse.ArgumentParser()
parser.add_argument(
    "--output",
    type=Path,
    default=OPTIONS_RST,
    help="Path to write the generated OPTIONS.rst content.",
)
args = parser.parse_args()

lead_in: list[str] = []

with OPTIONS_RST.open() as options_rst:
    for line in options_rst:
        lead_in.append(line)
        if DELIMITER_STR in line:
            break

output: TextIO
output = args.output.open("w")

for line in lead_in:
    output.write(line)


def _print(s: str = "") -> None:
    output.write(s + "\n")


def rst_code_block(help_str: str) -> None:
    _print(".. code::")
    _print()
    for line in help_str.split("\n"):
        _print(("  " + line) if line else "")
    _print()


ctx = click.Context(trezorctl.cli, info_name="trezorctl", terminal_width=99)
rst_code_block(trezorctl.cli.get_help(ctx))

for subcommand in sorted(trezorctl.cli.commands):
    cmd = trezorctl.cli.commands[subcommand]
    if not isinstance(cmd, click.Group):
        continue

    heading = cmd.get_short_help_str(limit=99)
    _print(heading)
    _print("~" * len(heading))
    _print()
    rst_code_block(f"trezorctl {subcommand} --help")
    ctx = click.Context(cmd, info_name=f"trezorctl {subcommand}", terminal_width=99)
    rst_code_block(cmd.get_help(ctx))

output.close()
