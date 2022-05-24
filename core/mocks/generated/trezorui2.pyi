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
INFO: object


# rust/src/ui/model_tr/layout.rs
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


# rust/src/ui/model_tr/layout.rs
def request_pin(
    *,
    prompt: str,
    subprompt: str | None = None,
    allow_cancel: bool | None = None,
    shuffle: bool | None = None,
) -> str | object:
    """Request pin on device."""


# rust/src/ui/model_tr/layout.rs
def confirm_text(
    *,
    title: str,
    data: str,
    description: str | None,
) -> object:
    """Confirm text."""


# rust/src/ui/model_tr/layout.rs
def show_share_words(
    *,
    share_words: str,  # words delimited by "," ... TODO: support list[str]
) -> None:
    """Shows a backup seed."""


# rust/src/ui/model_tr/layout.rs
def confirm_word(
    *,
    choices: str,  # words delimited by "," ... TODO: support list[str]
    checked_index: int,
    count: int,
    share_index: int | None,
    group_index: int | None,
) -> None:
    """Shows a backup seed."""
CONFIRMED: object
CANCELLED: object
INFO: object


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
) -> str | object:
    """Request pin on device."""


# rust/src/ui/model_tt/layout.rs
def request_passphrase(
    *,
    prompt: str,
    max_len: int,
) -> str | object:
   """Passphrase input keyboard."""


# rust/src/ui/model_tt/layout.rs
def request_bip39(
    *,
    prompt: str,
) -> str:
   """BIP39 word input keyboard."""


# rust/src/ui/model_tt/layout.rs
def request_slip39(
    *,
    prompt: str,
) -> str:
   """SLIP39 word input keyboard."""
