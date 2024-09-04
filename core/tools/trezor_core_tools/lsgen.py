#!/usr/bin/env python3
from __future__ import annotations

import click

from .common import  get_linkerscript_for_model, MODELS_DIR
from .layout_parser import find_all_values

@click.command()
@click.option("--check", is_flag=True)
def main(check: bool) -> None:

    models = list(MODELS_DIR.iterdir())
    models = [model for model in models if model.is_dir()]

    for model in models:
        values = find_all_values(model.name)
        content = ""
        for name, value in values.items():
            content += f"{name} = {hex(value)};\n"
        if not check:
            get_linkerscript_for_model(model.name).write_text(content)
        else:
            #todo
            pass


if __name__ == "__main__":
    main()
