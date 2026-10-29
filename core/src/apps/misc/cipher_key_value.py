from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import CipheredKeyValue, CipherKeyValue

# This module implements the SLIP-0011 symmetric encryption of key-value pairs using a
# deterministic hierarchy, see https://github.com/satoshilabs/slips/blob/master/slip-0011.md.


async def cipher_key_value(msg: CipherKeyValue) -> CipheredKeyValue:
    from trezorcrypto import cipher_key_value as native_cipher

    from trezor import TR
    from trezor.messages import CipheredKeyValue
    from trezor.ui.layouts import confirm_action
    from trezor.wire import DataError

    from apps.common.keychain import get_keychain
    from apps.common.paths import AlwaysMatchingSchema

    keychain = await get_keychain("secp256k1", [AlwaysMatchingSchema])

    if len(msg.value) % 16 > 0:
        raise DataError("Value length must be a multiple of 16")

    encrypt = msg.encrypt
    decrypt = not msg.encrypt
    if (encrypt and msg.ask_on_encrypt) or (decrypt and msg.ask_on_decrypt):
        # Special case for Trezor Suite, which asks for setting up labels
        if msg.key == "Enable labeling?":
            title = TR.misc__title_suite_labeling
            description = TR.misc__enable_labeling
            verb = TR.buttons__enable
        else:
            title = TR.misc__encrypt_value if encrypt else TR.misc__decrypt_value
            description = msg.key
            verb = TR.buttons__confirm

        await confirm_action(
            "cipher_key_value",
            title,
            description=description,
            verb=verb,
            prompt_screen=True,
        )

    node = keychain.derive(msg.address_n)

    value = native_cipher(
        node,
        msg.key.encode(),
        msg.value,
        bool(msg.encrypt),
        bool(msg.ask_on_encrypt),
        bool(msg.ask_on_decrypt),
        msg.iv or b"",
    )

    return CipheredKeyValue(value=value)
