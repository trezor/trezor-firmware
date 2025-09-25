from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EvoluDelegatedIdentityKey, EvoluGetDelegatedIdentityKey


async def get_delegated_identity_key(
    msg: EvoluGetDelegatedIdentityKey,
) -> EvoluDelegatedIdentityKey:
    from trezor import utils, wire
    from trezor.messages import EvoluDelegatedIdentityKey
    from trezor.utils import bootloader_locked

    if not bootloader_locked():
        raise wire.ProcessError("Cannot enable labeling since bootloader is unlocked.")

    if not utils.USE_OPTIGA:
        raise RuntimeError("Optiga is not available")

    if utils.USE_THP:
        await confirm_thp(msg)
    else:
        await confirm_no_thp()

    private_key = get_delegated_private_key()

    return EvoluDelegatedIdentityKey(private_key=private_key)


def get_delegated_private_key() -> bytes:
    from trezor.utils import delegated_identity

    key = delegated_identity()
    return bytes(key)


async def confirm_thp(msg: EvoluGetDelegatedIdentityKey) -> None:
    from trezor import TR
    from trezor.ui.layouts import confirm_action

    from apps.thp.credential_manager import decode_credential, validate_credential

    print(msg.thp_credentials)
    if msg.thp_credentials is None:
        raise ValueError("THP credentials must be provided when THP is enabled")
    if msg.host_static_public_key is None:
        raise ValueError("Host static public key must be provided when THP is enabled")

    credentials_received = decode_credential(msg.thp_credentials)

    if not validate_credential(credentials_received, msg.host_static_public_key):
        raise ValueError("Invalid credential")

    app_name = credentials_received.cred_metadata.app_name
    host_name = credentials_received.cred_metadata.host_name
    await confirm_action(
        "enable_labeling",
        TR.evolu__enable_labeling_header,
        TR.evolu__enable_labeling_message.format(app_name, host_name),
    )


async def confirm_no_thp() -> None:
    from trezor import TR
    from trezor.ui.layouts import confirm_action

    await confirm_action(
        "enable_labeling",
        TR.evolu__enable_labeling_header,
        TR.evolu__enable_labeling_message_no_thp,
    )
