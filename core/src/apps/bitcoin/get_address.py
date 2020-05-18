from trezor.crypto import bip32
from trezor.messages import InputScriptType
from trezor.messages.Address import Address

from apps.common.layout import address_n_to_str, show_address, show_qr, show_xpub
from apps.common.paths import validate_path

from . import addresses
from .keychain import with_keychain
from .multisig import multisig_pubkey_index

if False:
    from typing import List
    from trezor.messages import HDNodeType
    from trezor import wire
    from apps.common.coininfo import CoinInfo


async def show_xpubs(
    ctx: wire.Context, coin: CoinInfo, pubnodes: List[HDNodeType], multisig_index: int
) -> bool:
    for i, pubnode in enumerate(pubnodes):
        cancel = "Next" if i < len(pubnodes) - 1 else "Address"
        node = bip32.HDNode(
            depth=pubnode.depth,
            fingerprint=pubnode.fingerprint,
            child_num=pubnode.child_num,
            chain_code=pubnode.chain_code,
            public_key=pubnode.public_key,
            curve_name=coin.curve_name,
        )
        xpub = node.serialize_public(coin.xpub_magic)
        desc = "XPUB #%d" % (i + 1)
        desc += " (yours)" if i == multisig_index else " (others)"
        if await show_xpub(ctx, xpub, desc=desc, cancel=cancel):
            return True
    return False


@with_keychain
async def get_address(ctx, msg, keychain, coin):
    await validate_path(
        ctx,
        addresses.validate_full_path,
        keychain,
        msg.address_n,
        coin.curve_name,
        coin=coin,
        script_type=msg.script_type,
    )

    node = keychain.derive(msg.address_n)
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
            multisig_index = multisig_pubkey_index(msg.multisig, node.public_key())
            desc = "Multisig %d of %d" % (msg.multisig.m, len(pubnodes))
            while True:
                if await show_address(ctx, address_short, desc=desc):
                    break
                if await show_qr(ctx, address_qr, desc=desc, cancel="XPUBs"):
                    break
                if await show_xpubs(ctx, coin, pubnodes, multisig_index):
                    break
        else:
            desc = address_n_to_str(msg.address_n)
            while True:
                if await show_address(ctx, address_short, desc=desc):
                    break
                if await show_qr(ctx, address_qr, desc=desc):
                    break

    return Address(address=address)
