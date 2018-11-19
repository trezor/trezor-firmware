from trezor.messages import InputScriptType
from trezor.messages.Address import Address

from apps.common import coins, seed
from apps.common.layout import address_n_to_str, show_address, show_qr
from apps.common.paths import validate_path
from apps.wallet.sign_tx import addresses


async def get_address(ctx, msg):
    coin_name = msg.coin_name or "Bitcoin"
    coin = coins.by_name(coin_name)

    await validate_path(
        ctx,
        addresses.validate_full_path,
        path=msg.address_n,
        coin=coin,
        script_type=msg.script_type,
    )

    node = await seed.derive_node(ctx, msg.address_n, curve_name=coin.curve_name)
    address = addresses.get_address(msg.script_type, coin, node, msg.multisig)
    address_short = addresses.address_short(coin, address)

    if msg.show_display:
        if msg.multisig:
            desc = "Multisig %d of %d" % (msg.multisig.m, len(msg.multisig.pubkeys))
        else:
            desc = address_n_to_str(msg.address_n)
        while True:
            if await show_address(ctx, address_short, desc=desc):
                break
            if await show_qr(
                ctx,
                address.upper()
                if msg.script_type == InputScriptType.SPENDWITNESS
                else address,
                desc=desc,
            ):
                break

    return Address(address=address)
