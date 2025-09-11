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
    from trezor.ui.layouts.common import raise_if_cancelled
    from trezorui_api import confirm_thp_pairing

    if app_name and host_name:
        args = (app_name, host_name)
        description = long_text
    else:
        args = (app_name or host_name or "(unknown)",)
        description = short_text

    return raise_if_cancelled(
        confirm_thp_pairing(title=title, description=description, args=args),
        br_name=br_name,
    )


def show_autoconnect_credential_confirmation_screen(
    host_name: str | None,
    app_name: str | None,
) -> Awaitable[None]:
    from trezor import TR

    return confirm_pairing(
        br_name="thp_autoconnect_credential_request",
        title=TR.thp__autoconnect_title,
        app_name=app_name,
        host_name=host_name,
        short_text=TR.thp__autoconnect,
        long_text=TR.thp__autoconnect_app,
    )


def show_pairing_dialog(host_name: str | None, app_name: str | None) -> Awaitable[None]:
    from trezor import TR

    return confirm_pairing(
        br_name="thp_pairing_request",
        title=TR.thp__pair_title,
        app_name=app_name,
        host_name=host_name,
        short_text=TR.thp__pair,
        long_text=TR.thp__pair_app,
    )


def show_connection_dialog(
    host_name: str | None, app_name: str | None
) -> Awaitable[None]:
    from trezor import TR

    return confirm_pairing(
        br_name="thp_connection_request",
        title=TR.thp__connect_title,
        app_name=app_name,
        host_name=host_name,
        short_text=TR.thp__connect,
        long_text=TR.thp__connect_app,
    )


async def show_code_entry_screen(
    code_entry_str: str, host_name: str | None
) -> UiResult:
    from trezor import TR
    from trezor.ui.layouts.common import interact
    from trezorui_api import show_thp_pairing_code

    return await interact(
        show_thp_pairing_code(
            title=TR.thp__code_title,
            description=TR.thp__code_entry.format(host_name),
            code=code_entry_str,
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
