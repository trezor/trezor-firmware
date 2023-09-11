# !/usr/bin/env python3
from json import load

import click
from mako.template import Template


@click.command()
@click.argument("template_path", type=str)
@click.option("-p", "--programs-path", type=str, default=None)
@click.option("-o", "--out-file", type=click.File(mode="w"), default="-")
def render(template_path, programs_path, out_file):
    if programs_path is None:
        programs_path = template_path

    with open(f"{programs_path}/programs.json", "r") as file:
        programs = load(file)

    template = Template(filename=f"{template_path}/instructions.py.mako")

    out_file.write(template.render(programs=programs))


if __name__ == "__main__":
    render()
