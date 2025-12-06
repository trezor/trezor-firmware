from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EvoluDelegatedIdentityKey, EvoluGetDelegatedIdentityKey

from trezor import utils


async def get_delegated_identity_key(
    msg: EvoluGetDelegatedIdentityKey,
) -> EvoluDelegatedIdentityKey:
    """
    Retrieves the delegated identity private key for this device.
    This key is used

    1. to provide the identity of this device to the Quota Manager server.
    2. to authenticate the Suite to the Quota Manager server in future Suite Sync requests.
    3. as a token of the user's trust in this Trezor - Suite communication. Subsequent Suite Sync requests
    to this Trezor will be authenticated using this key, so we can skip more user confirmations.

    On devices with THP, we require a valid THP credential to be provided in the `msg`. The metadata from the credential
    is then displayed to the user during the confirmation. On devices without THP a generic confirmation dialog is shown.

    Args:
        msg (EvoluGetDelegatedIdentityKey): The incoming request message containing parameters for the operation.
    Returns:
        EvoluDelegatedIdentityKey: The response message containing the delegated identity private key.
    Raises:
        ValueError: If THP is enabled but the credential is missing or invalid.
    """

    from trezorutils import delegated_identity

    from trezor.messages import EvoluDelegatedIdentityKey

    if utils.USE_THP:
        await confirm_thp(msg)
    else:
        await confirm_no_thp()

    private_key = delegated_identity()

    return EvoluDelegatedIdentityKey(private_key=private_key)


async def confirm_no_thp() -> None:
    from trezor import TR
    from trezor.ui.layouts import confirm_action

    await confirm_action(
        "secure_sync",
        TR.secure_sync__header,
        TR.secure_sync__delegated_identity_key_no_thp,
    )


if utils.USE_THP:

    async def confirm_thp(msg: EvoluGetDelegatedIdentityKey) -> None:
        from trezor import TR
        from trezor.ui.layouts import confirm_action

        from apps.thp.credential_manager import decode_credential, validate_credential

        if msg.thp_credential is None:
            raise ValueError("THP credentials must be provided when THP is enabled")
        credential_received = decode_credential(msg.thp_credential)
        host_static_public_key = get_host_static_public_key()

        if not validate_credential(credential_received, host_static_public_key):
            raise ValueError("Invalid credential")

        app_name = credential_received.cred_metadata.app_name
        host_name = credential_received.cred_metadata.host_name
        await confirm_action(
            "secure_sync",
            TR.secure_sync__header,
            TR.secure_sync__delegated_identity_key_thp.format(app_name, host_name),
        )

    def get_host_static_public_key() -> bytes:
        from trezor.wire import context
        from trezor.wire.thp.session_context import GenericSessionContext

        ctx = context.get_context()
        if not isinstance(ctx, GenericSessionContext):
            raise Exception("Invalid THP session context")
        return ctx.channel.get_host_static_public_key()
