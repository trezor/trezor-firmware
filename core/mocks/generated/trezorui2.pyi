from typing import *


# extmod/rustmods/modtrezorui2.c
def layout_new_example(text: str) -> None:
    """Example layout."""


# extmod/rustmods/modtrezorui2.c
def layout_new_confirm_action(
    title: str | None,
    action: str | None,
    description: str | None,
    verb: str | None,
    verb_cancel: str | None,
    hold: bool | None,
    reverse: bool,
) -> int:
    """Confirm generic action. All arguments must be passed as kwargs."""


# extmod/rustmods/modtrezorui2.c
def layout_new_confirm_reset(
    prompt: str,
) -> int:
    """Confirm device setup. All arguments must be passed as kwargs."""


# extmod/rustmods/modtrezorui2.c
def layout_new_path_warning(
    path: str,
    title: str,
) -> int:
    """Show invalid derivation path warning. All arguments must be passed as kwargs."""


# extmod/rustmods/modtrezorui2.c
def layout_new_show_address(
    title: str,
    address: str,
    network: str | None,
    extra: str | None,
) -> int:
    """Show address. All arguments must be passed as kwargs."""


# extmod/rustmods/modtrezorui2.c
def layout_new_show_modal(
    title: str | None,
    subtitle: str | None,
    content: str,
    button_confirm: str | None,
    button_cancel: str | None,
) -> int:
    """Show success/error/warning. All arguments must be passed as kwargs."""


# extmod/rustmods/modtrezorui2.c
def layout_new_confirm_output(
    title: str,
    subtitle: str | None,
    address: str,
    amount: str,
) -> int:
    """Confirm output/recipient. All arguments must be passed as kwargs."""


# extmod/rustmods/modtrezorui2.c
def layout_new_confirm_total(
    title: str,
    label1: str,
    amount1: str,
    label2: str,
    amount2: str,
) -> int:
    """Final tx confirm. All arguments must be passed as kwargs."""


# extmod/rustmods/modtrezorui2.c
def layout_new_confirm_metadata(
    title: str,
    content: str,
    show_continue: bool,
) -> int:
    """Confirm tx metadata. All arguments must be passed as kwargs."""


# extmod/rustmods/modtrezorui2.c
def layout_new_confirm_blob(
    title: str,
    description: str | None,
    data: str,
) -> int:
    """Confirm arbitrary data. All arguments must be passed as kwargs."""


# extmod/rustmods/modtrezorui2.c
def layout_new_confirm_modify_fee(
    title: str,
    sign: int,
    user_fee_change: str,
    total_fee_new: str,
) -> int:
    """Confirm fee change. All arguments must be passed as kwargs."""


# extmod/rustmods/modtrezorui2.c
def layout_new_confirm_coinjoin(
    title: str,
    fee_per_anonymity: str | None,
    total_fee: str,
) -> int:
    """Confirm coinjoin. All arguments must be passed as kwargs."""
