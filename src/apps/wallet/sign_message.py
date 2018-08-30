from trezor import wire
from trezor.crypto.curve import secp256k1
from trezor.messages.InputScriptType import SPENDADDRESS, SPENDP2SHWITNESS, SPENDWITNESS
from trezor.messages.MessageSignature import MessageSignature
from trezor.ui.text import Text

from apps.common import coins, seed
from apps.common.confirm import require_confirm
from apps.common.signverify import message_digest, split_message
from apps.wallet.sign_tx.addresses import get_address


async def sign_message(ctx, msg):
    message = msg.message
    address_n = msg.address_n
    coin_name = msg.coin_name or "Bitcoin"
    script_type = msg.script_type or 0
    coin = coins.by_name(coin_name)

    await require_confirm_sign_message(ctx, message)

    node = await seed.derive_node(ctx, address_n, curve_name=coin.curve_name)
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


async def require_confirm_sign_message(ctx, message):
    message = split_message(message)
    text = Text("Sign message", new_lines=False)
    text.normal(*message)
    await require_confirm(ctx, text)
