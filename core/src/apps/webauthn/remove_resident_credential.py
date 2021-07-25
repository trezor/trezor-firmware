import storage.device
import storage.resident_credentials
from trezor import wire
from trezor.messages import Success, WebAuthnRemoveResidentCredential

from apps.common.confirm import require_confirm

from .confirm import ConfirmContent, ConfirmInfo
from .credential import Fido2Credential
from .resident_credentials import get_resident_credential


class ConfirmRemoveCredential(ConfirmInfo):
    def __init__(self, cred: Fido2Credential):
        super().__init__()
        self._cred = cred
        self.load_icon(cred.rp_id_hash)

    def get_header(self) -> str:
        return "Remove credential"

    def app_name(self) -> str:
        return self._cred.app_name()

    def account_name(self) -> str | None:
        return self._cred.account_name()


async def remove_resident_credential(
    ctx: wire.Context, msg: WebAuthnRemoveResidentCredential
) -> Success:
    if not storage.device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    if msg.index is None:
        raise wire.ProcessError("Missing credential index parameter.")

    cred = get_resident_credential(msg.index)
    if cred is None:
        raise wire.ProcessError("Invalid credential index.")

    content = ConfirmContent(ConfirmRemoveCredential(cred))
    await require_confirm(ctx, content)

    assert cred.index is not None
    storage.resident_credentials.delete(cred.index)
    return Success(message="Credential removed")
