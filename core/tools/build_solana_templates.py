# !/usr/bin/env python3
from json import load

import click
from mako.template import Template


@click.command()
@click.argument("template_path", type=str)
@click.option("-o", "--outfile", type=click.File(mode="w"), default="-")
def render(template_path, outfile):
    with open(f"{template_path}/programs.json", "r") as file:
        programs = load(file)

    init_template = Template(filename=f"{template_path}/instructions.py.mako")

    outfile.write(init_template.render(programs=programs))


if __name__ == "__main__":
    render()
