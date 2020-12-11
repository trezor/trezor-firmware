from trezor import wire
from trezor.messages.WebAuthnCredential import WebAuthnCredential
from trezor.messages.WebAuthnCredentials import WebAuthnCredentials
from trezor.messages.WebAuthnListResidentCredentials import (
    WebAuthnListResidentCredentials,
)
from trezor.ui.components.tt.text import Text

from apps.common.confirm import require_confirm

from . import resident_credentials


async def list_resident_credentials(
    ctx: wire.Context, msg: WebAuthnListResidentCredentials
) -> WebAuthnCredentials:
    text = Text("List credentials")
    text.normal(
        "Do you want to export",
        "information about the",
        "resident credentials",
        "stored on this device?",
    )
    await require_confirm(ctx, text)
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
