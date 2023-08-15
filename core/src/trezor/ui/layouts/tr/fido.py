import trezorui2
from trezor.enums import ButtonRequestType

from ..common import interact
from . import RustLayout


async def confirm_fido(
    header: str,
    app_name: str,
    icon_name: str | None,
    accounts: list[str | None],
) -> int:
    """Webauthn confirmation for one or more credentials."""
    confirm = RustLayout(
        trezorui2.confirm_fido(  # type: ignore [Argument missing for parameter "icon_name"]
            title=header.upper(),
            app_name=app_name,
            accounts=accounts,
        )
    )
    result = await interact(confirm, "confirm_fido", ButtonRequestType.Other)

    # The Rust side returns either an int or `CANCELLED`. We detect the int situation
    # and assume cancellation otherwise.
    if isinstance(result, int):
        return result

    # For the usage in device tests, assuming CONFIRMED (sent by debuglink)
    # is choosing the first credential.
    if __debug__ and result is trezorui2.CONFIRMED:
        return 0

    # Late import won't get executed on the happy path.
    from trezor.wire import ActionCancelled

    raise ActionCancelled


async def confirm_fido_reset() -> bool:
    confirm = RustLayout(
        trezorui2.confirm_action(
            title="FIDO2 RESET",
            description="Do you really want to erase all credentials?",
            action=None,
            verb_cancel="",
            verb="CONFIRM",
        )
    )
    return (await confirm) is trezorui2.CONFIRMED
