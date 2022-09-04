from __future__ import annotations

from pathlib import Path
from objects import OBJECTS, Object
from helpers import (
    beginning,
    run,
    indent_list,
    indent,
    command_teardown,
    breakpoint_and_command,
)

HERE = Path(__file__).parent
FILE = HERE / "size_info.gdb.generated"


def attribute_sizes(obj: Object) -> str:
    def attr_size(attr: str) -> str:
        return f'printf "{obj.name}.{attr}: %d\\n", sizeof(self.{attr})'

    return indent_list([attr_size(attr) for attr in obj.attributes])


def get_command_content(obj: Object, cmd_index: int) -> str:
    return "\n".join(
        [
            indent(f'printf "{obj.comment}\\n"'),
            indent(f'printf "{obj.name}: %d\\n", sizeof(*self)'),
            attribute_sizes(obj),
            command_teardown(cmd_index, obj.show_only_once, obj.continue_after_cmd),
        ]
    )


if __name__ == "__main__":
    with open(FILE, "w") as f:
        f.write(beginning("size_info"))
        f.write("\n")

        for index, obj in enumerate(OBJECTS, start=1):
            cmd_content = get_command_content(obj, index)
            f.write(breakpoint_and_command(obj, index, cmd_content))
            f.write("\n")

        f.write(run())
