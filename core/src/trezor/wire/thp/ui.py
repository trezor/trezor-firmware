from ..protocol_common import Context


async def show_autoconnect_credential_confirmation_screen(
    ctx: Context,
    host_name: str | None,
    device_name: str | None = None,
) -> None:
    from trezor.ui.layouts import confirm_action

    if not device_name:
        action_string = f"Allow {host_name} to connect automatically to this Trezor?"
    else:
        action_string = f"Allow {host_name} on {device_name} to connect automatically to this Trezor?"

    await confirm_action(
        br_name="thp_autoconnect_credential_request",
        title="Autoconnect credential",
        action=action_string,
    )
