from typing import TYPE_CHECKING

from trezor import translations, utils

if TYPE_CHECKING:
    from typing import Iterable, overload

    from .common import StrPropertyType

    @overload
    def with_colon(properties: None) -> None: ...
    @overload
    def with_colon(properties: Iterable[StrPropertyType]) -> list[StrPropertyType]: ...
    @overload
    def with_colon(properties: str) -> str: ...

    @overload
    def maybe_with_colon(properties: None) -> None: ...
    @overload
    def maybe_with_colon(
        properties: Iterable[StrPropertyType],
    ) -> list[StrPropertyType]: ...
    @overload
    def maybe_with_colon(properties: str) -> str: ...


def with_colon(
    properties: Iterable[StrPropertyType] | str | None = None,
) -> list[StrPropertyType] | str | None:
    if properties is None:
        return None

    NBSP = "\u00a0"
    separator = f"{NBSP}:" if translations.get_language() == "fr" else ":"
    if isinstance(properties, str):
        if properties:
            return f"{properties}{separator}"
        else:
            return ""

    return [((p[0] + separator if p[0] else p[0]),) + p[1:] for p in properties]


def maybe_with_colon(
    properties: Iterable[StrPropertyType] | str | None = None,
):
    """Add a colon to the end of the first element of each property tuple if the UI layout should have colons"""
    if utils.UI_LAYOUT in ("BOLT", "CAESAR"):
        return with_colon(properties)
    else:
        return properties
