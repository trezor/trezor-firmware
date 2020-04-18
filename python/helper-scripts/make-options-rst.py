#!/usr/bin/env python3

import os

import click

from trezorlib.cli import trezorctl

DELIMITER_STR = "### ALL CONTENT BELOW IS GENERATED"

options_rst = open(os.path.dirname(__file__) + "/../docs/OPTIONS.rst", "r+")

lead_in = []

for line in options_rst:
    lead_in.append(line)
    if DELIMITER_STR in line:
        break

options_rst.seek(0)
options_rst.truncate(0)

for line in lead_in:
    options_rst.write(line)


def _print(s=""):
    options_rst.write(s + "\n")


def rst_code_block(help_str):
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
