#!/usr/bin/env python3
from __future__ import annotations

import re

import click
import ast

from .common import get_layout_for_model


# the following regular expression matches a thing looking like those examples:
#   #define HEADER_START 0x123456
#   #define HEADER_START (1 * 2 * 3) // comment
# and returns two groups: the name and the value. Comment is ignored.
SEARCH_PATTERN = r"#define (\w+) (.+?)(?:\s*//.*)?$"


def find_all_values(model: str, secmon: bool) -> dict[str, int]:
    layout = get_layout_for_model(model, secmon)
    values = {}
    begin = False
    for line in open(layout):
        if not begin:
            if line.startswith("// SHARED"):
                begin = True
            continue
        match = re.match(SEARCH_PATTERN, line)
        if match is not None:
            name, value = match.groups()
            try:
                node = ast.parse(value, mode="eval")
                parsed_value = eval(compile(node, "<string>", "eval"))
                values[name] = int(parsed_value)
            except Exception:
                pass
    return values


def find_value(model: str, name: str, secmon: bool) -> int:
    all_values = find_all_values(model, secmon)
    if name not in all_values:
        raise ValueError(f"Value {name} not found in layout for model {model}")
    return all_values[name]


@click.command()
@click.argument("model")
@click.argument("name")
@click.option("--secmon", is_flag=True)
def main(model: str, name: str, secmon:bool) -> None:
    try:
        print(find_value(model, name, secmon))
    except ValueError as e:
        raise click.ClickException(str(e))


if __name__ == "__main__":
    main()
