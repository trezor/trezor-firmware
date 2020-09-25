from trezor.crypto import bip32
from trezor.messages import InputScriptType
from trezor.messages.Address import Address

from apps.common.confirm import interact
from apps.common.layout import address_n_to_str, show_xpub
from apps.common.paths import validate_path

from . import addresses
from .keychain import with_keychain
from .multisig import multisig_pubkey_index

if False:
    from typing import List
    from trezor.messages.GetAddress import GetAddress
    from trezor.messages.HDNodeType import HDNodeType
    from trezor import wire
    from apps.common.keychain import Keychain
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
async def get_address(
    ctx: wire.Context, msg: GetAddress, keychain: Keychain, coin: CoinInfo
) -> Address:
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
            multisig_n = len(pubnodes)
            while True:
                if await interact(
                    ctx,
                    "show_address",
                    address=address_short,
                    multisig_m=str(msg.multisig.m),
                    multisig_n=str(multisig_n),
                ):
                    break
                if await interact(
                    ctx,
                    "show_qr",
                    address=address_qr,
                    multisig_m=str(msg.multisig.m),
                    multisig_n=str(multisig_n),
                ):
                    break
                if await show_xpubs(ctx, coin, pubnodes, multisig_index):
                    break
        else:
            while True:
                if await interact(
                    ctx,
                    "show_address",
                    address=address_short,
                    address_path=address_n_to_str(msg.address_n),
                ):
                    break
                if await interact(
                    ctx,
                    "show_qr",
                    address=address_qr,
                    address_path=address_n_to_str(msg.address_n),
                ):
                    break

    return Address(address=address)
