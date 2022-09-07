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
def confirm_reset_device(
    *,
    title: str,
    prompt: str,
) -> object:
    """Confirm TOS before device setup."""


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
def show_error(
    *,
    title: str,
    button: str,
    description: str = "",
    allow_cancel: bool = False,
) -> object:
    """Error modal."""


# rust/src/ui/model_tt/layout.rs
def show_warning(
    *,
    title: str,
    button: str,
    description: str = "",
    allow_cancel: bool = False,
) -> object:
    """Warning modal."""


# rust/src/ui/model_tt/layout.rs
def show_success(
    *,
    title: str,
    button: str,
    description: str = "",
    allow_cancel: bool = False,
) -> object:
    """Success modal."""


# rust/src/ui/model_tt/layout.rs
def show_info(
    *,
    title: str,
    button: str,
    description: str = "",
    allow_cancel: bool = False,
) -> object:
    """Info modal."""


# rust/src/ui/model_tt/layout.rs
def show_simple(
    *,
    title: str | None,
    description: str,
    button: str,
) -> object:
    """Simple dialog with text and one button."""


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


# rust/src/ui/model_tt/layout.rs
def select_word(
    *,
    title: str,
    description: str,
    words: Iterable[str],
) -> int:
   """Select mnemonic word from three possibilities - seed check after backup. The
   iterable must be of exact size. Returns index in range `0..3`."""


# rust/src/ui/model_tt/layout.rs
def show_share_words(
    *,
    title: str,
    pages: Iterable[str],
) -> object:
   """Show mnemonic for backup. Expects the words pre-divided into individual pages."""


# rust/src/ui/model_tt/layout.rs
def request_number(
    *,
    title: str,
    count: int,
    min_count: int,
    max_count: int,
    description: Callable[[int], str],
) -> object:
   """Number input with + and - buttons, description, and info button."""


# rust/src/ui/model_tt/layout.rs
def show_checklist(
    *,
    title: str,
    items: Iterable[str],
    active: int,
    button: str,
) -> object:
   """Checklist of backup steps. Active index is highlighted, previous items have check
   mark nex to them."""
