from trezor import ui, wire
from trezor.messages.Success import Success
from trezor.messages.WebAuthnAddResidentCredential import WebAuthnAddResidentCredential
from trezor.ui.text import Text

from apps.common.confirm import require_confirm
from apps.common.storage.webauthn import store_resident_credential
from apps.webauthn.confirm import ConfirmContent, ConfirmInfo
from apps.webauthn.credential import Fido2Credential

if False:
    from typing import Optional


class ConfirmAddCredential(ConfirmInfo):
    def __init__(self, cred: Fido2Credential):
        self._cred = cred
        self.load_icon(cred.rp_id_hash)

    def get_header(self) -> str:
        return "Import credential"

    def app_name(self) -> str:
        return self._cred.app_name()

    def account_name(self) -> Optional[str]:
        return self._cred.account_name()


async def add_resident_credential(
    ctx: wire.Context, msg: WebAuthnAddResidentCredential
) -> Success:
    if not msg.credential_id:
        raise wire.ProcessError("Missing credential ID parameter.")

    cred = Fido2Credential.from_cred_id(msg.credential_id, None)
    if cred is None:
        text = Text("Import credential", ui.ICON_WRONG, ui.RED)
        text.normal(
            "The credential you are",
            "trying to import does",
            "not belong to this",
            "authenticator.",
        )
        await require_confirm(ctx, text, confirm=None)
        raise wire.ActionCancelled("Cancelled")

    content = ConfirmContent(ConfirmAddCredential(cred))
    await require_confirm(ctx, content)

    if store_resident_credential(cred):
        return Success(message="Credential added")
    else:
        raise wire.ProcessError("Internal credential storage is full.")
