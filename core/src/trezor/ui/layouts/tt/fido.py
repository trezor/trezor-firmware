import trezorui2
from trezor import ui
from trezor.enums import ButtonRequestType

from ..common import interact


async def confirm_fido(
    header: str,
    app_name: str,
    icon_name: str | None,
    accounts: list[str | None],
) -> int:
    """Webauthn confirmation for one or more credentials."""
    confirm = trezorui2.confirm_fido(
        title=header,
        app_name=app_name,
        icon_name=icon_name,
        accounts=accounts,
    )
    result = await interact(confirm, "confirm_fido", ButtonRequestType.Other)

    if __debug__ and result is trezorui2.CONFIRMED:
        # debuglink will directly inject a CONFIRMED message which we need to handle
        # by playing back a click to the Rust layout and getting out the selected number
        # that way
        from trezor import io

        confirm.touch_event(io.TOUCH_START, 220, 220)
        if confirm.paint():
            ui.refresh()
        msg = confirm.touch_event(io.TOUCH_END, 220, 220)
        if confirm.paint():
            ui.refresh()
        assert msg is trezorui2.LayoutState.DONE
        retval = confirm.return_value()
        assert isinstance(retval, int)
        return retval

    # The Rust side returns either an int or `CANCELLED`. We detect the int situation
    # and assume cancellation otherwise.
    if isinstance(result, int):
        return result

    # Late import won't get executed on the happy path.
    from trezor.wire import ActionCancelled

    raise ActionCancelled


async def confirm_fido_reset() -> bool:
    from trezor import TR

    confirm = ui.Layout(
        trezorui2.confirm_action(
            title=TR.fido__title_reset,
            action=TR.fido__erase_credentials,
            description=TR.words__really_wanna,
            reverse=True,
        )
    )
    return (await confirm.get_result()) is trezorui2.CONFIRMED
