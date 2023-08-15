from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Success, WebAuthnAddResidentCredential


async def add_resident_credential(msg: WebAuthnAddResidentCredential) -> Success:
    import storage.device as storage_device
    from trezor import wire
    from trezor.messages import Success
    from trezor.ui.layouts import show_error_and_raise
    from trezor.ui.layouts.fido import confirm_fido

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
            "warning_credential",
            "The credential you are trying to import does\nnot belong to this authenticator.",
        )

    await confirm_fido(
        "Import credential",
        cred.app_name(),
        cred.icon_name(),
        [cred.account_name()],
    )

    if store_resident_credential(cred):
        return Success(message="Credential added")
    else:
        raise wire.ProcessError("Internal credential storage is full.")
