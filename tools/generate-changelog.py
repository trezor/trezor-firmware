#!/usr/bin/env python3

import datetime
from pathlib import Path
import re
import subprocess

import click

LINK_RE = re.compile(r"\[#(\d+)\]")
ISSUE_URL = "https://github.com/trezor/trezor-firmware/issues/{issue}"

VERSION_HEADER_RE = re.compile(r"## \[([.0-9]+)\]")
DIFF_LINK = "[{new}]: https://github.com/trezor/trezor-firmware/compare/{tag_prefix}{old}...{tag_prefix}{new}\n"


def linkify_changelog(changelog_file, only_check=False):
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


def linkify_gh_diff(changelog_file, tag_prefix):
    linkified = False
    versions = []
    result_lines = []

    with open(changelog_file, "r+") as changelog:
        for line in changelog:
            m = VERSION_HEADER_RE.match(line)
            if m:
                versions.append(m[1])
            result_lines.append(line)

        changelog.seek(0)
        changelog.truncate(0)
        for line in result_lines:
            changelog.write(line)
            if not linkified and VERSION_HEADER_RE.match(line):
                changelog.write(
                    DIFF_LINK.format(
                        tag_prefix=tag_prefix, new=versions[0], old=versions[1]
                    )
                )
                linkified = True


def current_date(project):
    parts = project.parts
    today = datetime.datetime.now()

    if (
        parts[-3:] == ("core", "embed", "bootloader")
        or parts[-3:] == ("core", "embed", "bootloader_ci")
        or parts[-2:] == ("legacy", "bootloader")
        or parts[-2:] == ("legacy", "intermediate_fw")
    ):
        return today.strftime("%B %Y")
    elif parts[-1] == "python":
        return today.strftime("%Y-%m-%d")
    else:
        daysuffix = {1: "st", 2: "nd", 3: "rd"}.get(today.day % 10, "th")
        return today.strftime(f"%d{daysuffix} %B %Y")


@click.command()
@click.argument(
    "project",
    type=click.Path(exists=True, dir_okay=True, file_okay=False, resolve_path=True),
)
@click.argument(
    "version",
    type=str,
    required=False,
)
@click.option("--date", help="Specify release date (default: today).")
@click.option(
    "--check", is_flag=True, help="Dry run, do not actually create changelog."
)
def cli(project, version, date, check):
    """Generate changelog for given project (core, python, legacy/firmware,
    legacy/bootloader).

    - Run towncrier to assemble changelog from fragments in .changelog.d/.

    - Find all occurences of "[#123]" in text, and add a Markdown link to the
      referenced issue.

    - Tell git to stage changed files.
    """
    project = Path(project)
    changelog = project / "CHANGELOG.md"

    if not changelog.exists():
        raise click.ClickException(f"{changelog} not found")

    if version is None:
        if not check:
            raise click.ClickException("Version argument is required.")
        version = "unreleased"

    if date is None:
        date = current_date(project)

    args = ["towncrier", "build", "--yes", "--version", version, "--date", date]
    if check:
        args.append("--draft")
    subprocess.run(args, cwd=project, check=True)

    if not check:
        linkify_changelog(changelog)

        # python changelog has links to github diffs
        if project.parts[-1] == "python":
            linkify_gh_diff(changelog, tag_prefix="python/v")

        # towncrier calls git add before we do linkification, stage the changes too
        subprocess.run(["git", "add", changelog], check=True)


if __name__ == "__main__":
    cli()
