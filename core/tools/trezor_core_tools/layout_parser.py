#!/usr/bin/env python3
from __future__ import annotations


from pathlib import Path

import click
import ast


@click.command()
@click.argument(
    "layout",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
)
@click.argument(
    "name",
    type=click.STRING,
)
def main(
        layout: Path,
        name: str,
) -> None:

    search = f'#define {name} '
    for line in layout.read_text().splitlines():

        if line.startswith(search):
            line = line.split(search)[1]
            if line.startswith("("):
                line = line.split("(")[1].split(")")[-2]
            if "//" in line:
                line = line.split("//")[0]
            line = line.strip()
            node = ast.parse(line, mode='eval')
            result = eval(compile(node, '<string>', 'eval'))
            print(result)


if __name__ == "__main__":
    main()
