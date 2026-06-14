from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import DarkfiSignSpendAuth, DarkfiSpendAuthSignature


async def sign_spend_auth(msg: DarkfiSignSpendAuth) -> DarkfiSpendAuthSignature:
    from ubinascii import hexlify

    from trezor import TR
    from trezor.crypto import pallas
    from trezor.messages import DarkfiSpendAuthSignature
    from trezor.ui.layouts import (
        confirm_address,
        confirm_blob,
        confirm_properties,
        confirm_value,
    )
    from trezor.wire import DataError

    from . import account_spend_key

    alpha = msg.alpha
    sighash = msg.sighash

    if len(alpha) != 32:
        raise DataError("Invalid alpha length")

    # Show the human-readable spend summary the host claims this authorizes.
    details = msg.details
    if details is not None:
        # Amount: render "<value> <symbol>" using the host-supplied decimals and
        # token symbol when present (e.g. "1.5 DRK"). These two fields are a
        # display aid only; if the host omits them we fall back to the exact
        # smallest-unit integer and the raw token id, never a guessed scaling.
        from trezor.strings import format_amount

        if details.decimals is not None:
            amount_str = format_amount(details.value, details.decimals)
        else:
            amount_str = str(details.value)
        if details.symbol:
            amount_str = f"{amount_str} {details.symbol}"

        await confirm_value(
            TR.darkfi__authorize_spend,
            amount_str,
            None,
            "darkfi_spend_amount",
            subtitle=TR.darkfi__spend_value,
            verb=TR.buttons__continue,
        )

        # Extra cleartext context (token id, and any spend hook / user data) that
        # is meaningful only as hex; shown after the headline amount.
        props: list[tuple[str, str | bytes | None, bool | None]] = []
        if details.symbol is None:
            props.append((TR.darkfi__spend_token, hexlify(details.token_id), True))
        if details.spend_hook and details.spend_hook != bytes(32):
            props.append((TR.darkfi__spend_hook, hexlify(details.spend_hook), True))
        if details.user_data and details.user_data != bytes(32):
            props.append((TR.darkfi__spend_user_data, hexlify(details.user_data), True))
        if props:
            await confirm_properties(
                "darkfi_spend_details",
                TR.darkfi__authorize_spend,
                props,
            )

        # The recipient is a transmission key (pk_d), i.e. an address. Show it on
        # a dedicated address screen (chunked, paginable) rather than buried as a
        # hex row, so the user can actually scrutinise who they are paying. It is
        # omitted for atomic swaps, where the spent value has no single payable
        # recipient; there the headline amount above is the meaningful summary.
        if details.recipient:
            await confirm_address(
                TR.darkfi__spend_recipient,
                hexlify(details.recipient).decode(),
                br_name="darkfi_spend_recipient",
            )

    # Always show the exact message being signed, so a malicious host cannot
    # display benign details while signing a different sighash.
    await confirm_blob(
        "darkfi_sighash",
        TR.darkfi__transaction_id,
        hexlify(sighash).decode(),
        hold=True,
    )

    sk = await account_spend_key(msg.account)
    ask = pallas.derive_ask(sk)

    commit, rk, response = pallas.sign_spend_auth(ask, alpha, sighash)

    return DarkfiSpendAuthSignature(commit=commit, rk=rk, response=response)
