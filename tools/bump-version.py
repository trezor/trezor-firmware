#!/usr/bin/env python3

from pathlib import Path
import re

import click

VERSION_RE = re.compile(r"^(\d+)[.](\d+)[.](\d+)$")
HEADER_LINE_RE = re.compile(r"^#define ([A-Z_]+) \S+$")
PYTHON_VERSION_RE = re.compile(r'^__version__ = "\d+[.]\d+[.]\d+"$', flags=re.MULTILINE)


def bump_header(filename, **kwargs):
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


def bump_python(filename, new_version):
    with open(filename, "r+") as fh:
        contents = fh.read()
        result = PYTHON_VERSION_RE.sub(f'__version__ = "{new_version}"', contents)

        fh.seek(0)
        fh.truncate(0)
        fh.write(result)


def hex_lit(version):
    return r'"\x{:02X}"'.format(int(version))


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
    legacy/bootloader).
    """
    project = Path(project)

    m = VERSION_RE.match(version)
    if m is None:
        raise click.ClickException("Version must be MAJOR.MINOR.PATCH")

    major, minor, patch = m.group(1, 2, 3)

    parts = project.parts
    if parts[-1] == "core":
        bump_header(
            project / "embed" / "firmware" / "version.h",
            VERSION_MAJOR=major,
            VERSION_MINOR=minor,
            VERSION_PATCH=patch,
        )
    elif parts[-1] == "python":
        bump_python(
            project / "src" / "trezorlib" / "__init__.py", f"{major}.{minor}.{patch}"
        )
    elif parts[-2:] == ("legacy", "firmware"):
        bump_header(
            project / "version.h",
            VERSION_MAJOR=major,
            VERSION_MINOR=minor,
            VERSION_PATCH=patch,
        )
    elif parts[-2:] == ("legacy", "bootloader"):
        bump_header(
            project / "version.h",
            VERSION_MAJOR=major,
            VERSION_MINOR=minor,
            VERSION_PATCH=patch,
            VERSION_MAJOR_CHAR=hex_lit(major),
            VERSION_MINOR_CHAR=hex_lit(minor),
            VERSION_PATCH_CHAR=hex_lit(patch),
        )
    else:
        raise click.ClickException(f"Unknown project {project}.")


if __name__ == "__main__":
    cli()
