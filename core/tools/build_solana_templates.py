# !/usr/bin/env python3
from json import load

import click
from mako.template import Template
from munch import munchify


@click.command()
@click.argument("template_path", type=str)
@click.option("-p", "--programs-file", type=click.File(mode="r"), default="-")
@click.option("-o", "--out-file", type=click.File(mode="w"), default="-")
def render(template_path, programs_file, out_file):
    programs = munchify(load(programs_file))

    template = Template(filename=f"{template_path}/instructions.py.mako")

    out_file.write(template.render(programs=programs))


if __name__ == "__main__":
    render()
