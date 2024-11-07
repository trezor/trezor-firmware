from __future__ import annotations
import json
import os
import sys
from pathlib import Path

import click

HERE = Path(__file__).parent

language_file = HERE / "en.json"
output_file = HERE / "order.json"


def generate_new_order() -> None:
    translations = json.loads(language_file.read_text())["translations"]
    old_order: dict[str, str] = json.loads(output_file.read_text())

    old_unique_items: set[str] = set(old_order.values())
    new_unique_items: set[str] = set(translations.keys())

    new_items = sorted(new_unique_items - old_unique_items)
    if new_items:
        print("Found new items:")
        for item in new_items:
            print(item)

        first_update_index = len(old_order)
        for index, item in enumerate(new_items):
            new_index = str(first_update_index + index)
            print(f"Adding {item} to {new_index}")
            old_order[new_index] = item

        output_file.write_text(json.dumps(old_order, indent=2) + "\n")
        stat = language_file.stat()
        os.utime(output_file, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    else:
        print("No new items found.")


def check_order() -> None:
    old_order: dict[str, str] = json.loads(output_file.read_text())
    keys = { int(k) for k in old_order.keys() }
    for i in range(len(old_order)):
        if i not in keys:
            raise ValueError(f"order.json is missing index {i}")


@click.command()
@click.option("--check", is_flag=True, help="Do not modify order.json, only check if it's valid.")
def main(check: bool | None) -> None:
    check_order()
    if check:
        sys.exit(0)
    generate_new_order()


if __name__ == "__main__":
    main()
