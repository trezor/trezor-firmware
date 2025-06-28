#!/usr/bin/env python3
from __future__ import annotations

import itertools

import click

from .common import MODELS_DIR, get_layout_for_model, get_linkerscript_for_model
from .layout_parser import find_all_values

FILE_HEADER = """/* Auto-generated file, do not edit.*/

"""


def create_linker_script(model: str, cmse: bool) -> str:
    content = FILE_HEADER
    defines = find_all_values(model, cmse)
    for name, value in defines.items():
        content += f"{name} = {hex(value)};\n"
    return content


@click.command()
@click.option("--check", is_flag=True)
def main(check: bool) -> None:

    models = list(MODELS_DIR.iterdir())
    models = [model for model in models if model.is_dir()]

    for model, split in itertools.product(models, [False, True]):

        path = get_layout_for_model(model.name, split)
        if not path.exists():
            continue

        path = get_linkerscript_for_model(model.name, split)
        print(f"Processing {path}")

        new_content = create_linker_script(model.name, split)

        if check:
            current_content = path.read_text()
            if new_content != current_content:
                raise click.ClickException(f"{path} differs from expected")
        else:
            path.write_text(new_content)


if __name__ == "__main__":
    main()
