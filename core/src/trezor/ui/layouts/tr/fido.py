import trezorui_api
from trezor import ui
from trezor.enums import ButtonRequestType

from ..common import interact


async def confirm_fido(
    header: str,
    app_name: str,
    _icon_name: str | None,  # unused on TR
    accounts: list[str | None],
) -> int:
    """Webauthn confirmation for one or more credentials."""
    confirm = trezorui_api.confirm_fido(
        title=header,
        app_name=app_name,
        icon_name=None,
        accounts=accounts,
    )
    result = await interact(confirm, "confirm_fido", ButtonRequestType.Other)

    if isinstance(result, int):
        return result

    # For the usage in device tests, assuming CONFIRMED (sent by debuglink)
    # is choosing the first credential.
    if __debug__ and result is trezorui_api.CONFIRMED:
        return 0

    raise RuntimeError  # should not get here, cancellation is handled by `interact`


async def confirm_fido_reset() -> bool:
    from trezor import TR

    confirm = trezorui_api.confirm_action(
        title=TR.fido__title_reset,
        description=TR.fido__wanna_erase_credentials,
        action=None,
        verb_cancel="",
        verb=TR.buttons__confirm,
    )
    return (await ui.Layout(confirm).get_result()) is trezorui_api.CONFIRMED
