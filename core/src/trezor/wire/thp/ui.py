from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezorui_api import UiResult


def _app_on_host(app_name: str | None, host_name: str | None) -> str:
    if app_name and host_name:
        return f"{app_name} on {host_name}"
    elif not app_name and not host_name:
        return "(unknown)"
    else:
        return (app_name or "") + (host_name or "")


async def show_autoconnect_credential_confirmation_screen(
    host_name: str | None,
    app_name: str | None,
) -> None:
    from trezor.ui.layouts import confirm_action

    subject = _app_on_host(app_name, host_name)
    action_string = f"Allow {subject} to connect automatically to this Trezor?"

    await confirm_action(
        br_name="thp_autoconnect_credential_request",
        title="Autoconnect credential",
        action=action_string,
    )


async def show_connection_dialog(host_name: str | None, app_name: str | None) -> None:
    from trezor.ui.layouts import confirm_action

    subject = _app_on_host(app_name, host_name)
    action_string = f"Allow {subject} to connect with this Trezor?"

    await confirm_action(
        br_name="thp_connection_request",
        title="Connection dialog",
        action=action_string,
    )


async def show_code_entry_screen(
    code_entry_str: str, host_name: str | None
) -> UiResult:
    from trezor.ui.layouts.common import interact
    from trezorui_api import show_thp_pairing_code

    return await interact(
        show_thp_pairing_code(
            title="One more step",
            description=f"Enter this one-time security code on {host_name}",
            code=code_entry_str,
        ),
        br_name=None,
    )


async def show_nfc_screen() -> UiResult:
    from trezor.ui.layouts.common import interact
    from trezorui_api import show_simple

    return await interact(
        show_simple(
            title=None,
            text="Keep your Trezor near your phone to complete the setup.",
            button="Cancel",
        ),
        br_name=None,
    )


async def show_qr_code_screen(qr_code_str: str) -> UiResult:
    from trezor.ui.layouts.common import interact
    from trezorui_api import show_address_details

    return await interact(
        show_address_details(  # noqa
            qr_title="Scan QR code to pair",
            address=qr_code_str,
            case_sensitive=True,
            details_title="",
            account="",
            path="",
            xpubs=[],
        ),
        br_name=None,
    )
