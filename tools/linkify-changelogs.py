#!/usr/bin/env python3

import os
from pathlib import Path
import re

import click

LINK_RE = re.compile(r"\[#(\d+)\]")
ISSUE_URL = "https://github.com/trezor/trezor-firmware/issues/{issue}"

ROOT = Path(__file__).parent.resolve().parent

DEFAULT_CHANGELOGS = (  # TODO replace with a wildcard?
    ROOT / "core" / "CHANGELOG.md",
    ROOT / "legacy" / "firmware" / "CHANGELOG.md",
    ROOT / "legacy" / "bootloader" / "CHANGELOG.md",
    ROOT / "python" / "CHANGELOG.md",
)


def process_changelog(changelog_file, only_check=False):
    links = {}
    orig_links = {}
    result_lines = []

    with open(changelog_file, "r+") as changelog:
        for line in changelog:
            m = LINK_RE.match(line)
            if m:  # line *starts with* issue identifier
                # keep existing links as-is
                orig_links[int(m[1])] = line.replace(m[0] + ": ", "").strip()
            else:
                for issue in LINK_RE.findall(line):
                    links[int(issue)] = ISSUE_URL.format(issue=issue)
                result_lines.append(line)

        if only_check:
            missing_links = set(links.keys()) - set(orig_links.keys())
            if missing_links:
                click.echo(f"missing links: {missing_links}")
                return False
            else:
                return True

        links.update(orig_links)

        changelog.seek(0)
        changelog.truncate(0)
        for line in result_lines:
            changelog.write(line)
        for marker, url in sorted(links.items()):
            changelog.write(f"[#{marker}]: {url}\n")

    return True


@click.command()
@click.argument(
    "changelogs",
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False, writable=True),
)
@click.option("--check", is_flag=True, help="Check for missing links, do not modify.")
def cli(changelogs, check):
    """Linkify changelog.

    Find all occurences of "[#123]" in text, and add a Markdown link to the referenced
    issue.

    If no arguments are provided, runs on all known changelogs.
    """
    if not changelogs:
        changelogs = DEFAULT_CHANGELOGS

    all_ok = True
    for changelog in changelogs:
        click.echo(changelog)
        if not process_changelog(changelog, check):
            all_ok = False

    if not all_ok:
        raise click.ClickException("Some links are missing. Run `make style` to fix.")


if __name__ == "__main__":
    cli()
