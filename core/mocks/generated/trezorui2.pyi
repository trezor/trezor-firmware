from typing import *


# extmod/rustmods/modtrezorui2.c
def layout_new_confirm_action(
    *,
    title: str,
    action: str | None = None,
    description: str | None = None,
    verb: str | None = None,
    verb_cancel: str | None = None,
    hold: bool | None = None,
    reverse: bool = False,
) -> object:
    """Example layout."""


# extmod/rustmods/modtrezorui2.c
def layout_new_example(text: str) -> object:
    """Example layout."""


# extmod/rustmods/modtrezorui2.c
def layout_new_pin(
    *,
    prompt: str,
    subprompt: str,
    danger: bool,
    allow_cancel: bool,
) -> object:
    """PIN keyboard."""


# extmod/rustmods/modtrezorui2.c
def layout_new_confirm_text(
    *,
    title: str,
    data: str,
    description: str | None,
) -> object:
    """Example layout."""
