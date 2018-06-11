from trezor.messages import InputScriptType
from trezor.messages.Address import Address
from apps.common import coins, seed
from apps.common.display_address import show_qr, show_address
from apps.wallet.sign_tx import addresses


async def get_address(ctx, msg):
    coin_name = msg.coin_name or 'Bitcoin'
    coin = coins.by_name(coin_name)

    node = await seed.derive_node(ctx, msg.address_n)
    address = addresses.get_address(msg.script_type, coin, node, msg.multisig)
    address_short = address[len(coin.cashaddr_prefix) + 1:] if coin.cashaddr_prefix is not None else address

    if msg.show_display:
        while True:
            if await show_address(ctx, address_short):
                break
            if await show_qr(ctx, address.upper() if msg.script_type == InputScriptType.SPENDWITNESS else address):
                break

    return Address(address=address)
