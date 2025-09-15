from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from trezor.messages import EvoluGetDelegatedIdentityKey, EvoluDelegatedIdentityKey


async def get_delegated_identity_key(
    _msg: EvoluGetDelegatedIdentityKey,
) -> EvoluDelegatedIdentityKey:
    from trezor.messages import EvoluDelegatedIdentityKey

    from trezor import wire
    from trezor.ui.layouts import confirm_action
    from trezor.utils import bootloader_locked

    if not bootloader_locked():
        raise wire.ProcessError("Cannot enable labeling since bootloader is unlocked.")

    await confirm_action(  # ths should be TR.enable_labelig to allow translation
        "Enable labeling",  # but I am not sure how to do that and it is not needed now anyway
        f"Enable labeling",
        action=f"Do you want to enable labeling on this Suite?",
        prompt_screen=True,
    )

    private_key = get_delegetad_identity_key()
    public_key = get_public_key_from_private_key(private_key)

    return EvoluDelegatedIdentityKey(private_key=private_key, public_key=public_key)


def get_delegetad_identity_key() -> bytes:
    from trezor.utils import delegated_identity

    key = delegated_identity()
    return bytes(key)


def get_public_key_from_private_key(private_key: bytes) -> bytes:
    from trezor.crypto.curve import secp256k1

    public_key = secp256k1.publickey(private_key, False)
    return bytes(public_key)
