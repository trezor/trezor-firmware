from trezor import wire
from trezor.messages.Success import Success
from trezor.messages.WebAuthnRemoveResidentCredential import (
    WebAuthnRemoveResidentCredential,
)

from apps.common.confirm import require_confirm
from apps.common.storage.webauthn import (
    erase_resident_credential,
    get_resident_credential,
)
from apps.webauthn.confirm import ConfirmContent, ConfirmInfo
from apps.webauthn.credential import Fido2Credential

if False:
    from typing import Optional


class ConfirmRemoveCredential(ConfirmInfo):
    def __init__(self, cred: Fido2Credential):
        self._cred = cred
        self.load_icon(cred.rp_id_hash)

    def get_header(self) -> str:
        return "Remove credential"

    def app_name(self) -> str:
        return self._cred.app_name()

    def account_name(self) -> Optional[str]:
        return self._cred.account_name()


async def remove_resident_credential(
    ctx: wire.Context, msg: WebAuthnRemoveResidentCredential
) -> Success:
    if msg.index is None:
        raise wire.ProcessError("Missing credential index parameter.")

    cred = get_resident_credential(msg.index)
    if cred is None:
        raise wire.ProcessError("Invalid credential index.")

    content = ConfirmContent(ConfirmRemoveCredential(cred))
    await require_confirm(ctx, content)

    erase_resident_credential(msg.index)
    return Success(message="Credential removed")
