#!/usr/bin/env python3
import subprocess
from pathlib import Path

import click

ROOT = Path(__file__).parent.parent.resolve()


def load_symbols(elf_file: Path) -> list[str]:
    """Load symbol names from firmware ELF file using `nm`."""
    out = subprocess.check_output(
        args=["arm-none-eabi-nm", "--demangle", str(elf_file)]
    )
    symbols = (line.decode().split(maxsplit=2) for line in out.splitlines())
    return [name for _addr, type, name in symbols]


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.argument("elf_files", required=True, nargs=-1, type=click.Path(path_type=Path))
@click.option("-p", "--pattern", multiple=True, help="Must not appear in the ELF file")
def absent(elf_files: tuple[Path, ...], pattern: tuple[str, ...]) -> None:
    error = False
    for elf_file in elf_files:
        for symbol in load_symbols(elf_file):
            if any(p in symbol for p in pattern):
                click.echo(f"Unexpected symbol: `{symbol}` in {elf_file}")
                error = True

    if error:
        raise click.exceptions.Exit(1)


if __name__ == "__main__":
    cli()
