if False:
    from typing import TYPE_CHECKING
else:
    TYPE_CHECKING = False


if TYPE_CHECKING:
    from enum import IntEnum
% for enum in enums:

    class ${enum.name}(IntEnum):
% for value in enum.value:
        ${value.name} = ${value.number}
% endfor
% endfor
