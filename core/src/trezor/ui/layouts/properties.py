from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Iterable, overload

    from .common import StrPropertyType

    @overload
    def with_colon(properties: None) -> None: ...
    @overload
    def with_colon(properties: Iterable[StrPropertyType]) -> list[StrPropertyType]: ...
    @overload
    def with_colon(properties: str) -> str: ...


class AboveThreshold:
    """Signals that an amount exceeds a threshold.

    Passed to layout functions instead of a plain amount string so they can
    show the appropriate warning and display text.
    """

    def __init__(self, message: str) -> None:
        self.message = message


def with_colon(
    properties: Iterable[StrPropertyType] | str | None = None,
) -> list[StrPropertyType] | str | None:
    if properties is None:
        return None
    if isinstance(properties, str):
        if properties:
            return f"{properties}:"
        else:
            return ""

    return [((p[0] + ":" if p[0] else p[0]),) + p[1:] for p in properties]
