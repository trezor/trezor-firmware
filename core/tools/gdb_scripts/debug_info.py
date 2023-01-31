from __future__ import annotations

from pathlib import Path

from helpers import command_teardown, file_from_objects, indent_list
from objects import OBJECTS, Object

HERE = Path(__file__).parent
FILE = HERE / "debug_info.gdb.generated"


def get_command_content(obj: Object, cmd_index: int) -> str:
    return indent_list(
        [
            f'printf "{obj.name}: %d\\n", sizeof(*self)',
            "print self",
            "print *self",
            "",
            *command_teardown(cmd_index, obj.show_only_once, obj.continue_after_cmd),
        ]
    )


if __name__ == "__main__":
    file_from_objects(FILE, OBJECTS, get_command_content, "debug_info")
