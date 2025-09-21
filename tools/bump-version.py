#!/usr/bin/env python3

import re
import subprocess
from pathlib import Path

import click

VERSION_RE = re.compile(r"^(\d+)[.](\d+)[.](\d+)$")
HEADER_LINE_RE = re.compile(r"^#define ([A-Z_]+) \S+$")
VERSION_FILE_LINE_RE = re.compile(r"^([A-Z_]+) = \S+$")


def bump_header(filename: Path, **kwargs):
    result_lines = []

    with open(filename, "r+") as fh:
        for line in fh:
            m = HEADER_LINE_RE.match(line)
            if m is not None and m[1] in kwargs:
                symbol = m[1]
                result_lines.append(f"#define {symbol} {kwargs[symbol]}\n")
            else:
                result_lines.append(line)

        fh.seek(0)
        fh.truncate(0)
        for line in result_lines:
            fh.write(line)


def bump_version_file(filename: Path, **kwargs):
    result_lines = []

    with open(filename, "r+") as fh:
        for line in fh:
            m = VERSION_FILE_LINE_RE.match(line)
            if m is not None and m[1] in kwargs:
                symbol = m[1]
                result_lines.append(f"{symbol} = {kwargs[symbol]}\n")
            else:
                result_lines.append(line)

        fh.seek(0)
        fh.truncate(0)
        for line in result_lines:
            fh.write(line)


def bump_python(subdir: Path, new_version: str):
    subprocess.check_call(["uv", "version", new_version], cwd=subdir)


def hex_lit(version):
    return rf'"\x{int(version):02X}"'


@click.command()
@click.argument(
    "project",
    type=click.Path(exists=True, dir_okay=True, file_okay=False, resolve_path=True),
)
@click.argument(
    "version",
    type=str,
)
def cli(project, version):
    """Bump version for given project (core, python, legacy/firmware,
    legacy/bootloader, core/embed/projects/prodtest, nordic/trezor/trezor-ble).
    """
    project = Path(project)

    m = VERSION_RE.match(version)
    if m is None:
        raise click.ClickException("Version must be MAJOR.MINOR.PATCH")

    major, minor, patch = m.group(1, 2, 3)

    parts = project.parts
    if (project / "VERSION").is_file():
        bump_version_file(
            project / "VERSION",
            VERSION_MAJOR=major,
            VERSION_MINOR=minor,
            PATCHLEVEL=patch,
        )
    elif (project / "version.h").is_file():
        bump_header(
            project / "version.h",
            VERSION_MAJOR=major,
            VERSION_MINOR=minor,
            VERSION_PATCH=patch,
        )
    elif parts[-1] == "core":
        bump_header(
            project / "embed" / "projects" / "firmware" / "version.h",
            VERSION_MAJOR=major,
            VERSION_MINOR=minor,
            VERSION_PATCH=patch,
        )
        # also bump language JSONs
        subprocess.run(["python", project / "translations" / "cli.py", "gen"])
    elif parts[-1] == "legacy":
        bump_header(
            project / "firmware" / "version.h",
            VERSION_MAJOR=major,
            VERSION_MINOR=minor,
            VERSION_PATCH=patch,
        )
    elif parts[-1] == "python":
        bump_python(project / "python", f"{major}.{minor}.{patch}")
    else:
        raise click.ClickException(f"Unknown project {project}.")


if __name__ == "__main__":
    cli()
