from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EvoluDelegatedIdentityKey, EvoluGetDelegatedIdentityKey


async def get_delegated_identity_key(
    _msg: EvoluGetDelegatedIdentityKey,
) -> EvoluDelegatedIdentityKey:
    from trezor import utils, wire, TR
    from trezor.messages import EvoluDelegatedIdentityKey
    from trezor.ui.layouts import confirm_action
    from trezor.utils import bootloader_locked

    if not bootloader_locked():
        raise wire.ProcessError("Cannot enable labeling since bootloader is unlocked.")

    if not utils.USE_OPTIGA:
        raise RuntimeError("Optiga is not available")

    await confirm_action(
        "enable_labeling",
        TR.evolu__enable_labeling_header,
        TR.evolu__enable_labeling_message,
        prompt_screen=True,
    )

    private_key = get_delegated_private_key()

    return EvoluDelegatedIdentityKey(private_key=private_key)


def get_delegated_private_key() -> bytes:
    from trezor.utils import delegated_identity

    key = delegated_identity()
    return bytes(key)
