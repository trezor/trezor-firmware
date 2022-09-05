from __future__ import annotations

from pathlib import Path

from helpers import command_teardown, file_from_objects, indent_list
from objects import OBJECTS, Object

HERE = Path(__file__).parent
FILE = HERE / "size_info.gdb.generated"


def attribute_sizes(obj: Object) -> list[str]:
    def attr_size(attr: str) -> str:
        return f'printf "{obj.name}.{attr}: %d\\n", sizeof(self.{attr})'

    return [attr_size(attr) for attr in obj.attributes]


def get_command_content(obj: Object, cmd_index: int) -> str:
    return indent_list(
        [
            f'printf "{obj.comment}\\n"',
            f'printf "{obj.name}: %d\\n", sizeof(*self)',
            *attribute_sizes(obj),
            "",
            *command_teardown(cmd_index, obj.show_only_once, obj.continue_after_cmd),
        ]
    )


if __name__ == "__main__":
    file_from_objects(FILE, OBJECTS, get_command_content, "size_info")
