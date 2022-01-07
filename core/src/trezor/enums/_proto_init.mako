from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from enum import IntEnum
% for enum in enums:

    class ${enum.name}(IntEnum):
% for value in enum.value:
        ${value.name} = ${value.number}
% endfor
% endfor
