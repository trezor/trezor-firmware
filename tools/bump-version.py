#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import click

VERSION_RE = re.compile(r"^(\d+)[.](\d+)[.](\d+)(?:[.](\d+))?$")
HEADER_LINE_RE = re.compile(r"^#define ([A-Z_]+) \S+$")
VERSION_FILE_LINE_RE = re.compile(r"^([A-Z_]+) = \S+$")

SHORT = {
    "core": Path("embed/projects/firmware"),
    "legacy": Path("firmware"),
}
NO_BUILD = ["python", "legacy/*"]


def bump_re(pattern: re.Pattern, fmt: str, filename: Path, **kwargs: Any) -> None:
    result_lines = []

    with open(filename, "r+") as fh:
        for line in fh:
            m = pattern.match(line)
            if m is not None and kwargs.get(m[1]) is not None:
                symbol = m[1]
                result_lines.append(fmt.format(symbol=symbol, value=kwargs[symbol]))
            else:
                result_lines.append(line)

        fh.seek(0)
        fh.truncate(0)
        for line in result_lines:
            fh.write(line)


def bump_header(filename: Path, **kwargs: Any) -> None:
    return bump_re(HEADER_LINE_RE, "#define {symbol} {value}\n", filename, **kwargs)


def bump_version_file(filename: Path, **kwargs: Any) -> None:
    return bump_re(VERSION_FILE_LINE_RE, "{symbol} = {value}\n", filename, **kwargs)


def bump_python(subdir: Path, new_version: str) -> None:
    subprocess.check_call(["uv", "version", new_version], cwd=subdir)


@click.command()
@click.argument(
    "project",
    type=click.Path(exists=True, dir_okay=True, file_okay=False, resolve_path=True),
)
@click.argument(
    "version",
    type=str,
)
def cli(project: str | Path, version: str) -> None:
    """\b
    PROJECT must be a directory like:
    - core/embed/projects/firmware (shortcut: core)
    - core/embed/projects/bootloader
    - core/embed/projects/prodtest
    - python
    - nordic/trezor/trezor-ble
    - legacy/firmware (shortcut: legacy)
    - legacy/bootloader
    \b
    VERSION must be formatted like:
    - MAJOR.MINOR.PATCH (build is set to 0 if applicable)
    - MAJOR.MINOR.PATCH.BUILD (unsupported for legacy, python)
    """
    project = Path(project)
    if project.name in SHORT:
        project = project / SHORT[project.name]

    if (m := VERSION_RE.match(version)) is None:
        raise click.ClickException(
            "Version must be MAJOR.MINOR.PATCH or MAJOR.MINOR.PATCH.BUILD"
        )
    major, minor, patch, build = m.groups()

    if any(project.match(pat) for pat in NO_BUILD):
        if build is not None:
            raise click.ClickException(
                f"Version must be MAJOR.MINOR.PATCH for {project}."
            )
    elif build is None:
        build = 0

    if (project / "VERSION").is_file():
        bump_version_file(
            project / "VERSION",
            VERSION_MAJOR=major,
            VERSION_MINOR=minor,
            PATCHLEVEL=patch,
            VERSION_TWEAK=build,
        )
    elif (project / "version.h").is_file():
        bump_header(
            project / "version.h",
            VERSION_MAJOR=major,
            VERSION_MINOR=minor,
            VERSION_PATCH=patch,
            VERSION_BUILD=build,
        )
        if project.match("core/embed/projects/firmware"):
            # also bump language JSONs
            subprocess.check_call(
                ["python", project.parents[2] / "translations" / "cli.py", "gen"]
            )
        if project.match("core/embed/projects/prodtest"):
            # refresh error_codes.json
            subprocess.check_call(
                ["python", project.parents[2] / "tools" / "prodtest_error_codes.py"]
            )
    elif project.name == "python":
        bump_python(project, f"{major}.{minor}.{patch}")
    else:
        raise click.ClickException(f"Unknown project {project}.")


if __name__ == "__main__":
    cli()
