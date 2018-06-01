from trezor import ui, wire
from trezor.crypto.curve import secp256k1
from trezor.messages.InputScriptType import SPENDADDRESS, SPENDP2SHWITNESS, SPENDWITNESS
from trezor.messages.Success import Success
from trezor.ui.text import Text
from apps.common import coins
from apps.common.confirm import require_confirm
from apps.common.signverify import message_digest, split_message
from apps.wallet.sign_tx.addresses import address_pkh, address_p2wpkh_in_p2sh, address_p2wpkh, address_to_cashaddr
from apps.wallet.get_address import _split_address


async def verify_message(ctx, msg):
    message = msg.message
    address = msg.address
    signature = msg.signature
    coin_name = msg.coin_name or 'Bitcoin'
    coin = coins.by_name(coin_name)

    digest = message_digest(coin, message)

    script_type = None
    recid = signature[0]
    if recid >= 27 and recid <= 34:
        script_type = SPENDADDRESS  # p2pkh
    elif recid >= 35 and recid <= 38:
        script_type = SPENDP2SHWITNESS  # segwit-in-p2sh
        signature = bytes([signature[0] - 4]) + signature[1:]
    elif recid >= 39 and recid <= 42:
        script_type = SPENDWITNESS  # native segwit
        signature = bytes([signature[0] - 8]) + signature[1:]
    else:
        raise wire.ProcessError('Invalid signature')

    pubkey = secp256k1.verify_recover(signature, digest)

    if not pubkey:
        raise wire.ProcessError('Invalid signature')

    if script_type == SPENDADDRESS:
        addr = address_pkh(pubkey, coin.address_type)
        if coin.cashaddr_prefix is not None:
            addr = address_to_cashaddr(addr, coin)
    elif script_type == SPENDP2SHWITNESS:
        addr = address_p2wpkh_in_p2sh(pubkey, coin.address_type_p2sh)
    elif script_type == SPENDWITNESS:
        addr = address_p2wpkh(pubkey, coin.bech32_prefix)
    else:
        raise wire.ProcessError('Invalid signature')

    if addr != address:
        raise wire.ProcessError('Invalid signature')

    await require_confirm_verify_message(ctx, address, message)

    return Success(message='Message verified')


async def require_confirm_verify_message(ctx, address, message):
    lines = _split_address(address)
    content = Text('Confirm address', ui.ICON_DEFAULT, ui.MONO, *lines)
    await require_confirm(ctx, content)

    message = split_message(message)
    content = Text('Verify message', ui.ICON_DEFAULT, max_lines=5, *message)
    await require_confirm(ctx, content)
