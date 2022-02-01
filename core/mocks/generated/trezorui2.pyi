from typing import *


# extmod/rustmods/modtrezorui2.c
def layout_new_example(text: str) -> None:
    """Example layout."""


# extmod/rustmods/modtrezorui2.c
def layout_new_confirm_action(
    title: str,
    action: str | None,
    description: str | None,
    verb: str | None,
    verb_cancel: str | None,
    hold: bool | None,
    reverse: bool,
) -> int:
    """Example layout. All arguments must be passed as kwargs."""
