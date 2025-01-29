#!/usr/bin/env python3

import datetime
from pathlib import Path
import re
import subprocess

import click

from typing import Iterator

LINK_RE = re.compile(r"\[#(\d+)\]")
ISSUE_URL = "https://github.com/trezor/trezor-firmware/pull/{issue}"

VERSION_HEADER_RE = re.compile(r"## \[([.0-9]+)\]")
DIFF_LINK = "[{new}]: https://github.com/trezor/trezor-firmware/compare/{tag_prefix}{old}...{tag_prefix}{new}\n"

MODELS_RE = re.compile(r"\[([A-Z0-9]{4})(,[A-Z0-9]{4})*\][ ]?")
INTERNAL_MODELS = ("T2T1", "T2B1", "T3B1", "T3T1", "D001")
INTERNAL_MODELS_SKIP = ("D001",)

ROOT = Path(__file__).parent.parent.resolve()

# Source of truth for all managed changelogs in this repository.
# Please extend it when adding a new project with a managed changelog.
KNOWN_PROJECTS = (
    ROOT / "core",
    ROOT / "core/embed/projects/boardloader",
    ROOT / "core/embed/projects/bootloader",
    ROOT / "core/embed/projects/bootloader_ci",
    ROOT / "core/embed/projects/prodtest",
    ROOT / "legacy/bootloader",
    ROOT / "legacy/firmware",
    ROOT / "legacy/intermediate_fw",
    ROOT / "python",
)

for project in KNOWN_PROJECTS:
    assert project.is_dir(), f"Project {project} does not exist"

IGNORED_FILES = (".gitignore", ".keep")


def linkify_changelog(changelog_file: Path, only_check: bool = False) -> bool:
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


def linkify_gh_diff(changelog_file: Path, tag_prefix: str):
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


def current_date(project: Path) -> str:
    parts = project.parts
    today = datetime.datetime.now()

    if (
        parts[-3:] == ("core", "embed", "boardloader")
        or parts[-3:] == ("core", "embed", "bootloader")
        or parts[-3:] == ("core", "embed", "bootloader_ci")
        or parts[-2:] == ("legacy", "bootloader")
        or parts[-2:] == ("legacy", "intermediate_fw")
    ):
        return today.strftime("%B %Y")
    elif parts[-1] == "python":
        return today.strftime("%Y-%m-%d")
    else:
        daysuffix = {1: "st", 2: "nd", 3: "rd"}.get(today.day % 10, "th")
        return today.strftime(f"%-d{daysuffix} %B %Y")


def filter_changelog(changelog_file: Path, internal_name: str):
    def filter_line(line: str) -> str | None:
        m = MODELS_RE.search(line)
        if not m:
            return line
        if internal_name in m[0]:
            return MODELS_RE.sub("", line, count=1)
        else:
            return None

    destination_file = changelog_file.with_suffix(f".{internal_name}.md")
    with open(changelog_file, "r") as changelog, open(
        destination_file, "w"
    ) as destination:
        for line in changelog:
            res = filter_line(line)
            if res is not None:
                destination.write(res)


def _iter_fragments(project: Path) -> Iterator[Path]:
    fragments_dir = project / ".changelog.d"
    for fragment in fragments_dir.iterdir():
        if fragment.name in IGNORED_FILES:
            continue
        yield fragment


def check_fragments_style(project: Path):
    success = True
    for fragment in _iter_fragments(project):
        fragment_text = fragment.read_text().strip()
        if not fragment_text.endswith("."):
            click.echo(f"Changelog '{fragment}' must end with a period.")
            success = False
        if fragment_text.startswith("[") and not MODELS_RE.search(fragment_text):
            click.echo(f"Wrong model specifier in '{fragment}'")
            success = False

    if not success:
        raise click.ClickException(f"Changelog style error: {project}")
    else:
        click.echo(f"Changelog style OK: {project}")


def fix_fragments_style(project: Path):
    for fragment in _iter_fragments(project):
        fragment_text = fragment.read_text().rstrip()
        if not fragment_text.endswith("."):
            fragment.write_text(fragment_text + ".\n")
            click.echo(f"Changelog '{fragment}' style fixed.")


def generate_filtered(project: Path, changelog: Path):
    if project.parts[-1] != "core":
        return

    for internal_name in INTERNAL_MODELS:
        if internal_name in INTERNAL_MODELS_SKIP:
            continue
        filter_changelog(changelog, internal_name)


@click.group()
def cli():
    pass


@cli.command()
def check():
    """Check the style of all changelog fragments."""
    for project in KNOWN_PROJECTS:
        check_fragments_style(project)


@cli.command()
def style():
    """Fix the style of all changelog fragments."""
    for project in KNOWN_PROJECTS:
        fix_fragments_style(project)


@cli.command()
@click.argument(
    "project",
    type=click.Path(
        exists=True,
        dir_okay=True,
        file_okay=False,
        resolve_path=True,
        path_type=Path,
    ),
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
@click.option(
    "--only-models",
    is_flag=True,
    help="Only regenerate the model-changelogs from the main one.",
)
def generate(project, version, date, check, only_models):
    """Generate changelog for given project (core, python, legacy/firmware,
    legacy/bootloader).

    - Run towncrier to assemble changelog from fragments in .changelog.d/.

    - Find all occurences of "[#123]" in text, and add a Markdown link to the
      referenced issue.

    - Tell git to stage changed files.
    """
    if project not in KNOWN_PROJECTS:
        try:
            path_for_print = project.relative_to(ROOT)
        except ValueError:
            raise click.ClickException(
                f"Paths outside the repository are not supported (path was: {project})."
            )
        raise click.ClickException(
            f"Please add '{path_for_print}' to `KNOWN_PROJECTS` to be part of our managed changelogs."
        )

    changelog = project / "CHANGELOG.md"

    if not changelog.exists():
        raise click.ClickException(f"{changelog} not found")

    if version is None:
        if not check and not only_models:
            raise click.ClickException("Version argument is required.")
        version = "unreleased"

    if date is None:
        date = current_date(project)

    if only_models:
        generate_filtered(project, changelog)
        return 0

    args = ["towncrier", "build", "--yes", "--version", version, "--date", date]
    if check:
        args.append("--draft")
    subprocess.run(args, cwd=project, check=True)

    if not check:
        linkify_changelog(changelog)

        # python changelog has links to github diffs
        if project.parts[-1] == "python":
            linkify_gh_diff(changelog, tag_prefix="python/v")

        # core changelog for each model
        generate_filtered(project, changelog)

        # towncrier calls git add before we do linkification, stage the changes too
        subprocess.run(["git", "add", changelog], check=True)


if __name__ == "__main__":
    cli()
