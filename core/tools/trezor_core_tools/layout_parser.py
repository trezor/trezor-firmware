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


def find_all_values(model: str) -> dict[str, int]:
    layout = get_layout_for_model(model)
    values = {}
    for line in open(layout):
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


def find_value(model: str, name: str) -> int:
    all_values = find_all_values(model)
    if name not in all_values:
        raise ValueError(f"Value {name} not found in layout for model {model}")
    return all_values[name]


@click.command()
@click.argument("model")
@click.argument("name")
def main(model: str, name: str) -> None:
    try:
        print(find_value(model, name))
    except ValueError as e:
        raise click.ClickException(str(e))


if __name__ == "__main__":
    main()
