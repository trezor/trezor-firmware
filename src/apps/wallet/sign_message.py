from trezor import ui
from trezor.wire import FailureError
from trezor.crypto.curve import secp256k1
from trezor.messages.InputScriptType import SPENDADDRESS
from trezor.messages.FailureType import ProcessError
from trezor.messages.MessageSignature import MessageSignature
from trezor.ui.text import Text
from apps.common import coins, seed
from apps.common.confirm import require_confirm
from apps.common.signverify import message_digest, split_message


async def sign_message(ctx, msg):
    message = msg.message
    address_n = msg.address_n
    coin_name = msg.coin_name or 'Bitcoin'
    script_type = msg.script_type or 0
    coin = coins.by_name(coin_name)

    if script_type != SPENDADDRESS:
        raise FailureError(ProcessError, 'Unsupported script type')

    await confirm_sign_message(ctx, message)

    node = await seed.derive_node(ctx, address_n)
    seckey = node.private_key()

    address = node.address(coin.address_type)
    digest = message_digest(coin, message)
    signature = secp256k1.sign(seckey, digest)

    return MessageSignature(address=address, signature=signature)


async def confirm_sign_message(ctx, message):
    message = split_message(message)
    content = Text('Sign message', ui.ICON_CONFIRM, ui.MONO, *message)
    await require_confirm(ctx, content)
