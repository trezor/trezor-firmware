from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EvoluDelegatedIdentityKey, EvoluGetDelegatedIdentityKey


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

    from trezor import utils
    from trezor.messages import EvoluDelegatedIdentityKey
    from trezor.ui.layouts import confirm_action

    if msg.index_management:
        index = index_management(msg)
        return EvoluDelegatedIdentityKey(private_key=b"", rotation_index=index)

    if msg.rotate:
        from trezor import TR

        rotation_index = get_rotation_index(msg)
        if rotation_index is None:
            raise ValueError(
                "Cannot rotate delegated identity key without a stored rotation index."
            )

        await confirm_action(
            "secure_sync",
            TR.suite_sync__header,
            TR.suite_sync__rotate_key,
        )

        set_rotation_index(rotation_index + 1)
    else:
        if utils.USE_THP:
            await confirm_thp(msg)
        else:
            await confirm_no_thp()

    rotation_index = get_rotation_index(msg)
    if rotation_index is None:
        private_key = delegated_identity(0)
    else:
        private_key = delegated_identity(rotation_index)

    return EvoluDelegatedIdentityKey(
        private_key=private_key, rotation_index=rotation_index
    )


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
        TR.suite_sync__header,
        TR.suite_sync__delegated_identity_key_thp.format(app_name, host_name),
    )


async def confirm_no_thp() -> None:
    from trezor import TR
    from trezor.ui.layouts import confirm_action

    await confirm_action(
        "secure_sync",
        TR.suite_sync__header,
        TR.suite_sync__delegated_identity_key_no_thp,
    )


def get_rotation_index(msg: EvoluGetDelegatedIdentityKey) -> int | None:
    from storage.device import get_delegated_identity_key_rotation_index

    rotation_index = get_delegated_identity_key_rotation_index()

    if isinstance(msg.rotation_index, int):
        if rotation_index is None:
            rotation_index = msg.rotation_index
            set_rotation_index(rotation_index)
        if msg.rotation_index <= rotation_index:
            return msg.rotation_index
        else:
            raise ValueError(
                f"Provided rotation index {msg.rotation_index} is greater than the stored rotation index {rotation_index}."
            )

    return rotation_index


def index_management(msg: EvoluGetDelegatedIdentityKey) -> int | None:
    from storage.device import get_delegated_identity_key_rotation_index

    stored_index = get_delegated_identity_key_rotation_index()
    if stored_index is not None:
        return stored_index
    else:
        if msg.rotation_index is None:
            return None
        else:
            set_rotation_index(msg.rotation_index)
            return msg.rotation_index


def set_rotation_index(index: int) -> None:
    from storage.device import set_delegated_identity_key_rotation_index

    set_delegated_identity_key_rotation_index(index)
