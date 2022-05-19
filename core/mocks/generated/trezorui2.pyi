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


# rust/src/ui/model_tr/layout.rs
def request_word_count(
    *,
    title: str,
    text: str,
) -> str:  # TODO: make it return int
    """Get word count for recovery."""


# rust/src/ui/model_tr/layout.rs
def request_word_bip39(
    *,
    prompt: str,
) -> str:
    """Get recovery word for BIP39."""


# rust/src/ui/model_tr/layout.rs
def request_passphrase(
    *,
    prompt: str,
    max_len: int,
) -> str:
    """Get passphrase."""
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
    hold: bool = False,
    reverse: bool = False,
) -> object:
    """Confirm action."""


# rust/src/ui/model_tt/layout.rs
def confirm_blob(
    *,
    title: str,
    data: str,
    description: str = "",
    extra: str = "",
    verb_cancel: str | None = None,
    ask_pagination: bool = False,
    hold: bool = False,
) -> object:
    """Confirm byte sequence data."""


# rust/src/ui/model_tt/layout.rs
def show_qr(
    *,
    title: str,
    address: str,
    verb_cancel: str,
    case_sensitive: bool,
) -> object:
    """Show QR code."""


# rust/src/ui/model_tt/layout.rs
def confirm_output(
    *,
    title: str,
    description: str,
    value: str,
    verb: str = "NEXT",
) -> object:
    """Confirm output."""


# rust/src/ui/model_tt/layout.rs
def confirm_total(
    *,
    title: str,
    description: str,
    value: str,
) -> object:
    """Confirm total."""


# rust/src/ui/model_tt/layout.rs
def confirm_joint_total(
    *,
    spending_amount: str,
    total_amount: str,
) -> object:
    """Confirm total if there are external inputs."""


# rust/src/ui/model_tt/layout.rs
def confirm_modify_output(
    *,
    address: str,
    sign: int,
    amount_change: str,
    amount_new: str,
) -> object:
    """Decrease or increase amount for given address."""


# rust/src/ui/model_tt/layout.rs
def confirm_modify_fee(
    *,
    sign: int,
    user_fee_change: str,
    total_fee_new: str,
) -> object:
    """Decrease or increase transaction fee."""


# rust/src/ui/model_tt/layout.rs
def show_warning(
    *,
    title: str,
    description: str = "",
) -> object:
    """Warning modal."""


# rust/src/ui/model_tt/layout.rs
def show_success(
    *,
    title: str,
    button: str,
    description: str = "",
) -> object:
    """Success modal."""


# rust/src/ui/model_tt/layout.rs
def confirm_payment_request(
    *,
    description: str,
    memos: Iterable[str],
) -> object:
    """Confirm payment request."""


# rust/src/ui/model_tt/layout.rs
def confirm_coinjoin(
    *,
    coin_name: str,
    max_rounds: str,
    max_feerate: str,
) -> object:
    """Confirm coinjoin authorization."""


# rust/src/ui/model_tt/layout.rs
def request_pin(
    *,
    prompt: str,
    subprompt: str,
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
