from typing import *
CONFIRMED: object
CANCELLED: object


# rust/src/ui/model_t1/layout.rs
def confirm_action(
    *,
    title: str,
    action: str | None = None,
    description: str | None = None,
    verb: str | None = None,
    verb_cancel: str | None = None,
    hold: bool | None = None,
    reverse: bool = False,
) -> object:
    """Confirm action."""


# extmod/rustmods/modtrezorui2.c
def layout_new_example(text: str) -> object:
    """Example layout."""


# extmod/rustmods/modtrezorui2.c
def layout_new_pin(
    *,
    prompt: str,
    subprompt: str,
    allow_cancel: bool,
    warning: str | None,
) -> object:
    """PIN keyboard."""


# extmod/rustmods/modtrezorui2.c
def layout_new_passphrase(
    *,
    prompt: str,
    max_len: int,
) -> object:
    """Passphrase keyboard."""


# extmod/rustmods/modtrezorui2.c
def layout_new_bip39(
    *,
    prompt: str,
) -> object:
    """BIP39 keyboard."""


# extmod/rustmods/modtrezorui2.c
def layout_new_slip39(
    *,
    prompt: str,
) -> object:
    """BIP39 keyboard."""


# extmod/rustmods/modtrezorui2.c
def layout_new_confirm_text(
    *,
    title: str,
    data: str,
    description: str | None,
) -> object:
    """Confirm text."""
CONFIRMED: object
CANCELLED: object


# rust/src/ui/model_t1/layout.rs
def confirm_text(
    *,
    title: str,
    data: str,
    description: str | None,
) -> object:
    """Confirm text."""
CONFIRMED: object
CANCELLED: object


# rust/src/ui/model_tt/layout.rs
def confirm_action(
    *,
    title: str,
    action: str | None = None,
    description: str | None = None,
    verb: str | None = None,
    verb_cancel: str | None = None,
    hold: bool | None = None,
    reverse: bool = False,
) -> object:
    """Confirm action."""


# rust/src/ui/model_tt/layout.rs
def request_pin(
    *,
    prompt: str,
    subprompt: str | None = None,
    allow_cancel: bool = True,
    warning: str | None = None,
) -> str:
    """Request pin on device."
