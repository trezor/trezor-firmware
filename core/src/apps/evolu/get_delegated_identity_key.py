from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EvoluDelegatedIdentityKey, EvoluGetDelegatedIdentityKey


async def get_delegated_identity_key(
    _msg: EvoluGetDelegatedIdentityKey,
) -> EvoluDelegatedIdentityKey:
    from trezor import wire
    from trezor.messages import EvoluDelegatedIdentityKey
    from trezor.ui.layouts import confirm_action
    from trezor.utils import bootloader_locked

    if not bootloader_locked():
        raise wire.ProcessError("Cannot enable labeling since bootloader is unlocked.")

    await confirm_action(
        "Enable labeling",
        "Enable labeling",
        action="Do you want to enable labeling on this Suite?",
        prompt_screen=True,
    )

    private_key = get_delegated_private_key()
    public_key = get_public_key_from_private_key(private_key)

    return EvoluDelegatedIdentityKey(private_key=private_key, public_key=public_key)


def get_delegated_private_key() -> bytes:
    from trezor.utils import delegated_identity

    key = delegated_identity()
    return bytes(key)


def get_public_key_from_private_key(private_key: bytes) -> bytes:
    from trezor.crypto.curve import secp256k1

    public_key = secp256k1.publickey(private_key, False)
    return bytes(public_key)
