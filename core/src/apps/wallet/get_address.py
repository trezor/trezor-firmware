from trezor.crypto import bip32
from trezor.messages import InputScriptType
from trezor.messages.Address import Address

from apps.common import coins
from apps.common.layout import address_n_to_str, show_address, show_qr, show_xpub
from apps.common.paths import validate_path
from apps.wallet.sign_tx import addresses

if False:
    from typing import List
    from trezor.messages import HDNodeType
    from trezor import wire
    from apps.common.coininfo import CoinInfo


async def show_xpubs(
    ctx: wire.Context, coin: CoinInfo, pubnodes: List[HDNodeType]
) -> bool:
    for i, x in enumerate(pubnodes):
        cancel = "Next" if i < len(pubnodes) - 1 else "Address"
        node = bip32.HDNode(
            depth=x.depth,
            fingerprint=x.fingerprint,
            child_num=x.child_num,
            chain_code=x.chain_code,
            public_key=x.public_key,
            curve_name=coin.curve_name,
        )
        xpub = node.serialize_public(coin.xpub_magic)
        if await show_xpub(ctx, xpub, desc="XPUB #%d" % (i + 1), cancel=cancel):
            return True
    return False


async def get_address(ctx, msg, keychain):
    coin_name = msg.coin_name or "Bitcoin"
    coin = coins.by_name(coin_name)

    await validate_path(
        ctx,
        addresses.validate_full_path,
        keychain,
        msg.address_n,
        coin.curve_name,
        coin=coin,
        script_type=msg.script_type,
    )

    node = keychain.derive(msg.address_n, coin.curve_name)
    address = addresses.get_address(msg.script_type, coin, node, msg.multisig)
    address_short = addresses.address_short(coin, address)
    if msg.script_type == InputScriptType.SPENDWITNESS:
        address_qr = address.upper()  # bech32 address
    elif coin.cashaddr_prefix is not None:
        address_qr = address.upper()  # cashaddr address
    else:
        address_qr = address  # base58 address

    if msg.show_display:
        if msg.multisig:
            if msg.multisig.nodes:
                pubnodes = msg.multisig.nodes
            else:
                pubnodes = [hd.node for hd in msg.multisig.pubkeys]
            desc = "Multisig %d of %d" % (msg.multisig.m, len(pubnodes))
            while True:
                if await show_address(ctx, address_short, desc=desc):
                    break
                if await show_qr(ctx, address_qr, desc=desc, cancel="XPUBs"):
                    break
                if await show_xpubs(ctx, coin, pubnodes):
                    break
        else:
            desc = address_n_to_str(msg.address_n)
            while True:
                if await show_address(ctx, address_short, desc=desc):
                    break
                if await show_qr(ctx, address_qr, desc=desc):
                    break

    return Address(address=address)
