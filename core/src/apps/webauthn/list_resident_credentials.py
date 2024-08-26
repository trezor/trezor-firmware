from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WebAuthnCredentials, WebAuthnListResidentCredentials


async def list_resident_credentials(
    msg: WebAuthnListResidentCredentials,
) -> WebAuthnCredentials:
    from trezor import TR
    from trezor.messages import WebAuthnCredential, WebAuthnCredentials
    from trezor.ui.layouts import confirm_action

    from . import resident_credentials

    await confirm_action(
        "credentials_list",
        TR.fido__title_list_credentials,
        description=TR.fido__export_credentials,
        verb=TR.buttons__export,
        prompt_screen=True,
    )
    creds = [
        WebAuthnCredential(
            index=cred.index,
            id=cred.id,
            rp_id=cred.rp_id,
            rp_name=cred.rp_name,
            user_id=cred.user_id,
            user_name=cred.user_name,
            user_display_name=cred.user_display_name,
            creation_time=cred.creation_time,
            hmac_secret=cred.hmac_secret,
            use_sign_count=cred.use_sign_count,
            algorithm=cred.algorithm,
            curve=cred.curve,
        )
        for cred in resident_credentials.find_all()
    ]
    return WebAuthnCredentials(credentials=creds)
