from typing import TYPE_CHECKING

from trezor.ui.components.common.webauthn import ConfirmInfo

if TYPE_CHECKING:
    from trezor.messages import WebAuthnAddResidentCredential, Success
    from trezor.wire import Context
    from .credential import Fido2Credential


class ConfirmAddCredential(ConfirmInfo):
    def __init__(self, cred: Fido2Credential):
        super().__init__()
        self._cred = cred
        self.load_icon(cred.rp_id_hash)

    def get_header(self) -> str:
        return "Import credential"

    def app_name(self) -> str:
        return self._cred.app_name()

    def account_name(self) -> str | None:
        return self._cred.account_name()


async def add_resident_credential(
    ctx: Context, msg: WebAuthnAddResidentCredential
) -> Success:
    import storage.device as storage_device
    from trezor import wire
    from trezor.ui.layouts import show_error_and_raise
    from trezor.ui.layouts.webauthn import confirm_webauthn
    from trezor.messages import Success
    from .credential import Fido2Credential
    from .resident_credentials import store_resident_credential

    if not storage_device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    if not msg.credential_id:
        raise wire.ProcessError("Missing credential ID parameter.")

    try:
        cred = Fido2Credential.from_cred_id(bytes(msg.credential_id), None)
    except Exception:
        await show_error_and_raise(
            ctx,
            "warning_credential",
            "The credential you are trying to import does\nnot belong to this authenticator.",
            "Import credential",
            button="Close",
            red=True,
        )

    if not await confirm_webauthn(ctx, ConfirmAddCredential(cred)):
        raise wire.ActionCancelled

    if store_resident_credential(cred):
        return Success(message="Credential added")
    else:
        raise wire.ProcessError("Internal credential storage is full.")
