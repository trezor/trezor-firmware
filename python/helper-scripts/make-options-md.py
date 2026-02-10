#!/usr/bin/env python3

# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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

import os
from typing import List

import click

from trezorlib.cli import trezorctl

DELIMITER_STR = "### ALL CONTENT BELOW IS GENERATED"

options_md = open(os.path.dirname(__file__) + "/../docs/OPTIONS.md", "r+")

lead_in: List[str] = []

for line in options_md:
    lead_in.append(line)
    if DELIMITER_STR in line:
        break

options_md.seek(0)
options_md.truncate(0)

for line in lead_in:
    options_md.write(line)


def _print(s: str = "") -> None:
    options_md.write(s + "\n")


def rst_code_block(help_str: str) -> None:
    _print("```")
    for line in help_str.split("\n"):
        _print(line)
    _print("```")
    _print()


ctx = click.Context(trezorctl.cli, info_name="trezorctl", terminal_width=99)
rst_code_block(trezorctl.cli.get_help(ctx))

for subcommand in sorted(trezorctl.cli.commands):
    cmd = trezorctl.cli.commands[subcommand]
    if not isinstance(cmd, click.Group):
        continue

    heading = cmd.get_short_help_str(limit=99)
    _print("### " + heading)
    _print()
    rst_code_block(f"trezorctl {subcommand} --help")
    ctx = click.Context(cmd, info_name=f"trezorctl {subcommand}", terminal_width=99)
    rst_code_block(cmd.get_help(ctx))
