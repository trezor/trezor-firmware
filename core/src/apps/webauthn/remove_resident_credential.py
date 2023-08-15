from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Success, WebAuthnRemoveResidentCredential


async def remove_resident_credential(msg: WebAuthnRemoveResidentCredential) -> Success:
    import storage.device
    import storage.resident_credentials
    from trezor import wire
    from trezor.messages import Success
    from trezor.ui.layouts.fido import confirm_fido

    from .resident_credentials import get_resident_credential

    if not storage.device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    if msg.index is None:
        raise wire.ProcessError("Missing credential index parameter.")

    cred = get_resident_credential(msg.index)
    if cred is None:
        raise wire.ProcessError("Invalid credential index.")

    await confirm_fido(
        "Remove credential",
        cred.app_name(),
        cred.icon_name(),
        [cred.account_name()],
    )

    assert cred.index is not None
    storage.resident_credentials.delete(cred.index)
    return Success(message="Credential removed")
