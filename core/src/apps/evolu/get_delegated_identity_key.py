from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EvoluDelegatedIdentityKey, EvoluGetDelegatedIdentityKey


async def get_delegated_identity_key(
    msg: EvoluGetDelegatedIdentityKey,
) -> EvoluDelegatedIdentityKey:
    """
    Retrieves the delegated identity private key for this device.
    This key is used

    a) to provide identity of this devicee to the Gate server

    and b) as a token of user's trust in this Trezor - Suite communication. Subsequent Secure Sync requests
    to this Trezor will be authenticated using this key so we can skip more user confirmations.

    This function does not work if the bootloader is unlocked.

    On devices with THP, we require valid THP credential to be provided in the `msg`. The metadata from the credential
    are then displayed to the user during the confirmation. On devices without THP a generinc confirmation dialog is shown.

    Args:
        msg (EvoluGetDelegatedIdentityKey): The incoming request message containing parameters for the operation.
        THP credential is required if THP is available on the device.
    Returns:
        EvoluDelegatedIdentityKey: The response message containing the delegated identity private key.
    Raises:
        wire.ProcessError: If the bootloader is unlocked.
        RuntimeError: If Optiga is not available.
        ValueError: If THP is enabled but the credential is missing or invalid.
    """

    from trezorutils import delegated_identity

    from trezor import utils, wire
    from trezor.messages import EvoluDelegatedIdentityKey
    from trezor.utils import bootloader_locked

    if (
        bootloader_locked() is False
    ):  # cannot use `if not bootloader_locked()` since on None we do not want to raise an error
        raise wire.ProcessError(
            "Cannot enable Secure Sync since bootloader is unlocked."
        )

    if utils.USE_THP:
        await confirm_thp(msg)
    else:
        await confirm_no_thp()

    private_key = delegated_identity()

    return EvoluDelegatedIdentityKey(private_key=private_key)


async def confirm_thp(msg: EvoluGetDelegatedIdentityKey) -> None:
    from trezor import TR
    from trezor.ui.layouts import confirm_action

    from apps.thp.credential_manager import decode_credential, validate_credential

    if msg.thp_credential is None:
        raise ValueError("THP credentials must be provided when THP is enabled")
    if msg.host_static_public_key is None:
        raise ValueError("Host static public key must be provided when THP is enabled")

    credential_received = decode_credential(msg.thp_credential)

    if not validate_credential(credential_received, msg.host_static_public_key):
        raise ValueError("Invalid credential")

    app_name = credential_received.cred_metadata.app_name
    host_name = credential_received.cred_metadata.host_name
    await confirm_action(
        "secure_sync",
        TR.secure_sync__header,
        TR.secure_sync__delegated_identity_key_thp.format(app_name, host_name),
    )


async def confirm_no_thp() -> None:
    from trezor import TR
    from trezor.ui.layouts import confirm_action

    await confirm_action(
        "secure_sync",
        TR.secure_sync__header,
        TR.secure_sync__delegated_identity_key_no_thp,
    )
