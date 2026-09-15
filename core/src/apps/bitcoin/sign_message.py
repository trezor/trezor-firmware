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
        is_sign_message_account_node,
        is_sign_message_bip48_path,
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
    # Cosigners share the xpub at the BIP-48 account node, two levels above
    # the patterns in the naming table; account_level trims them to match, so
    # the node is named rather than left as "Unknown path" -- which would
    # contradict a path we allow without warning.
    #
    # A BIP-48 path is named by its level, passing no script type: the level
    # need not agree with the one asked for, and get_name() would otherwise
    # reject the entry and leave the same "Unknown path". The trimmed patterns
    # differ by level, so the level alone picks the name.
    account = address_n_to_name_or_unknown(
        coin,
        address_n,
        None if is_sign_message_bip48_path(coin, address_n) else script_type,
        account_level=is_sign_message_account_node(coin, address_n),
    )
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
