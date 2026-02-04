from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Iterable

    from .common import StrPropertyType


def with_colon(
    properties: Iterable[StrPropertyType] | None = None,
) -> list[StrPropertyType] | None:
    if properties is None:
        return None
    elif properties:
        return [((p[0] + ":" if p[0] else p[0]),) + p[1:] for p in properties]
    else:
        return []
