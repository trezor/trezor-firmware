#!/usr/bin/env python3
from __future__ import annotations

import click

from .common import  get_linkerscript_for_model, MODELS_DIR
from .layout_parser import find_all_values


warning = """/* Auto-generated file, do not edit.*/

"""

@click.command()
@click.option("--check", is_flag=True)
def main(check: bool) -> None:

    models = list(MODELS_DIR.iterdir())
    models = [model for model in models if model.is_dir()]

    for model in models:
        values = find_all_values(model.name)
        content = warning
        input = get_linkerscript_for_model(model.name)
        print(f"Processing {input}")
        for name, value in values.items():
            content += f"{name} = {hex(value)};\n"
        if not check:
            input.write_text(content)
        else:
            actual = input.read_text()
            if content != actual:
                raise click.ClickException(f"{input} differs from expected")


if __name__ == "__main__":
    main()
