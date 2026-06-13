from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import DarkfiSignSpendAuth, DarkfiSpendAuthSignature


async def sign_spend_auth(msg: DarkfiSignSpendAuth) -> DarkfiSpendAuthSignature:
    from ubinascii import hexlify

    from trezor import TR
    from trezor.crypto import pallas
    from trezor.messages import DarkfiSpendAuthSignature
    from trezor.ui.layouts import confirm_blob, confirm_properties
    from trezor.wire import DataError

    from . import account_spend_key

    alpha = msg.alpha
    sighash = msg.sighash

    if len(alpha) != 32:
        raise DataError("Invalid alpha length")

    # Show the human-readable spend summary the host claims this authorizes.
    details = msg.details
    if details is not None:
        props: list[tuple[str, str | bytes | None, bool | None]] = [
            (TR.darkfi__spend_value, str(details.value), None),
            (TR.darkfi__spend_token, hexlify(details.token_id), True),
            (TR.darkfi__spend_recipient, hexlify(details.recipient), True),
        ]
        if details.spend_hook and details.spend_hook != bytes(32):
            props.append((TR.darkfi__spend_hook, hexlify(details.spend_hook), True))
        if details.user_data and details.user_data != bytes(32):
            props.append((TR.darkfi__spend_user_data, hexlify(details.user_data), True))

        await confirm_properties(
            "darkfi_spend_details",
            TR.darkfi__authorize_spend,
            props,
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
