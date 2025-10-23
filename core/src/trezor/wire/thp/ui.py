from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Awaitable

    from trezorui_api import UiResult


def confirm_pairing(
    br_name: str,
    title: str,
    app_name: str | None,
    host_name: str | None,
    short_text: str,
    long_text: str,
) -> Awaitable[None]:
    from trezor.ui.layouts.common import raise_if_not_confirmed
    from trezorui_api import confirm_action

    if app_name and host_name:
        args = (app_name, host_name)
        description = long_text
    else:
        args = (app_name or host_name or "(unknown)",)
        description = short_text

    text = description.format(*args)

    return raise_if_not_confirmed(
        confirm_action(title=title, action=None, description=text),
        br_name=br_name,
    )


def show_autoconnect_credential_confirmation_screen(
    host_name: str | None,
    app_name: str | None,
) -> Awaitable[None]:

    return confirm_pairing(
        br_name="thp_autoconnect_credential_request",
        title="Autoconnect credential",
        app_name=app_name,
        host_name=host_name,
        short_text="Allow {0} to connect automatically to this Trezor?",
        long_text="Allow {0} on {1} to connect automatically to this Trezor?",
    )


def show_pairing_dialog(host_name: str, app_name: str) -> Awaitable[None]:
    from trezor import TR

    return confirm_pairing(
        br_name="thp_pairing_request",
        title="Before you continue",
        app_name=app_name,
        host_name=host_name,
        short_text="Allow {0} to pair with this Trezor?",
        long_text="Allow {0} on {1} to pair with this Trezor?",
    )


def show_connection_dialog(
    host_name: str | None, app_name: str | None
) -> Awaitable[None]:

    return confirm_pairing(
        br_name="thp_connection_request",
        title="Connection dialog",
        app_name=app_name,
        host_name=host_name,
        short_text="Allow {0} to connect with this Trezor?",
        long_text="Allow {0} on {1} to connect with this Trezor?",
    )


async def show_code_entry_screen(
    code_entry_str: str, host_name: str | None
) -> UiResult:
    from trezor.ui.layouts.common import interact
    from trezorui_api import show_simple

    return await interact(
        show_simple(
            text="Enter this one-time security code on {0}".format(host_name)
            + "\ncode: "
            + code_entry_str,
            title="One more step",
        ),
        br_name=None,
    )


async def show_nfc_screen() -> UiResult:
    from trezor import TR
    from trezor.ui.layouts.common import interact
    from trezorui_api import show_simple

    return await interact(
        show_simple(
            title=None,
            text=TR.thp__nfc_text,
            button=TR.buttons__cancel,
        ),
        br_name=None,
    )


async def show_qr_code_screen(qr_code_str: str) -> UiResult:
    from trezor import TR
    from trezor.ui.layouts.common import interact
    from trezorui_api import show_address_details

    return await interact(
        show_address_details(  # noqa
            qr_title=TR.thp__qr_title,
            address=qr_code_str,
            case_sensitive=True,
            details_title="",
            account="",
            path="",
            xpubs=[],
        ),
        br_name=None,
    )
