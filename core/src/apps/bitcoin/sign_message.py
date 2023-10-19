from typing import TYPE_CHECKING

from .keychain import with_keychain

if TYPE_CHECKING:
    from trezor.messages import MessageSignature, SignMessage

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain


@with_keychain
async def sign_message(
    msg: SignMessage, keychain: Keychain, coin: CoinInfo
) -> MessageSignature:
    from trezor import wire
    from trezor.crypto.curve import secp256k1
    from trezor.enums import InputScriptType
    from trezor.messages import MessageSignature
    from trezor.ui.layouts import confirm_signverify

    from apps.common.paths import address_n_to_str, validate_path
    from apps.common.signverify import decode_message, message_digest

    from .addresses import address_short, get_address
    from .keychain import (
        address_n_to_name_or_unknown,
        validate_path_against_script_type,
    )

    message = msg.message
    address_n = msg.address_n
    script_type = msg.script_type or InputScriptType.SPENDADDRESS

    await validate_path(
        keychain, address_n, validate_path_against_script_type(coin, msg)
    )

    node = keychain.derive(address_n)
    address = get_address(script_type, coin, node)
    path = address_n_to_str(address_n)
    account = address_n_to_name_or_unknown(coin, address_n, script_type)
    await confirm_signverify(
        decode_message(message),
        address_short(coin, address),
        verify=False,
        account=account,
        path=path,
        chunkify=bool(msg.chunkify),
    )

    seckey = node.private_key()

    digest = message_digest(coin, message)
    signature = secp256k1.sign(seckey, digest)

    if script_type == InputScriptType.SPENDADDRESS:
        script_type_info = 0
    elif script_type == InputScriptType.SPENDP2SHWITNESS:
        script_type_info = 4
    elif script_type == InputScriptType.SPENDWITNESS:
        script_type_info = 8
    else:
        raise wire.ProcessError("Unsupported script type")

    # Add script type information to the recovery byte.
    if script_type_info != 0 and not msg.no_script_type:
        signature = bytes([signature[0] + script_type_info]) + signature[1:]

    return MessageSignature(address=address, signature=signature)
