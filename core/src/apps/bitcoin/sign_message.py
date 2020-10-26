from trezor import wire
from trezor.crypto.curve import secp256k1
from trezor.messages.InputScriptType import SPENDADDRESS, SPENDP2SHWITNESS, SPENDWITNESS
from trezor.messages.MessageSignature import MessageSignature

from apps.common.paths import validate_path
from apps.common.signverify import message_digest, require_confirm_sign_message

from .addresses import get_address
from .keychain import with_keychain

if False:
    from trezor.messages.SignMessage import SignMessage

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain


@with_keychain
async def sign_message(
    ctx: wire.Context, msg: SignMessage, keychain: Keychain, coin: CoinInfo
) -> MessageSignature:
    message = msg.message
    address_n = msg.address_n
    script_type = msg.script_type or 0

    await validate_path(ctx, keychain, address_n)
    await require_confirm_sign_message(ctx, coin.coin_shortcut, message)

    node = keychain.derive(address_n)
    seckey = node.private_key()

    address = get_address(script_type, coin, node)
    digest = message_digest(coin, message)
    signature = secp256k1.sign(seckey, digest)

    if script_type == SPENDADDRESS:
        pass
    elif script_type == SPENDP2SHWITNESS:
        signature = bytes([signature[0] + 4]) + signature[1:]
    elif script_type == SPENDWITNESS:
        signature = bytes([signature[0] + 8]) + signature[1:]
    else:
        raise wire.ProcessError("Unsupported script type")

    return MessageSignature(address=address, signature=signature)
