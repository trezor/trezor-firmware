import trezorui_api

from ..protocol_common import Context


async def show_autoconnect_credential_confirmation_screen(
    ctx: Context,
    host_name: str | None,
    device_name: str | None = None,
) -> None:
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts.common import raise_if_cancelled

    if not device_name:
        action_string = f"Allow {host_name} to connect automatically to this Trezor?"
    else:
        action_string = f"Allow {host_name} on {device_name} to connect automatically to this Trezor?"

    await raise_if_cancelled(
        trezorui_api.confirm_action(
            title="Autoconnect credential",
            action=action_string,
            description=None,
        ),
        br_name="thp_autoconnect_credential_request",
        br_code=ButtonRequestType.Other,
    )
