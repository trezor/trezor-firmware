from trezor.crypto import bip32
from trezor.messages import InputScriptType
from trezor.messages.Address import Address

from apps.common.layout import address_n_to_str, show_address, show_qr, show_xpub
from apps.common.paths import validate_path

from . import addresses
from .keychain import validate_path_against_script_type, with_keychain
from .multisig import multisig_pubkey_index

if False:
    from typing import List
    from trezor.messages.GetAddress import GetAddress
    from trezor.messages.HDNodeType import HDNodeType
    from trezor import wire
    from apps.common.keychain import Keychain
    from apps.common.coininfo import CoinInfo


async def show_xpubs(
    ctx: wire.Context,
    coin: CoinInfo,
    xpub_magic: int,
    pubnodes: List[HDNodeType],
    multisig_index: int,
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
        xpub = node.serialize_public(xpub_magic)
        desc = "XPUB #%d" % (i + 1)
        desc += " (yours)" if i == multisig_index else " (others)"
        if await show_xpub(ctx, xpub, desc=desc, cancel=cancel):
            return True
    return False


@with_keychain
async def get_address(
    ctx: wire.Context, msg: GetAddress, keychain: Keychain, coin: CoinInfo
) -> Address:
    if msg.show_display:
        # skip soft-validation for silent calls
        await validate_path(
            ctx,
            keychain,
            msg.address_n,
            validate_path_against_script_type(coin, msg),
        )

    node = keychain.derive(msg.address_n)

    address = addresses.get_address(msg.script_type, coin, node, msg.multisig)
    address_short = addresses.address_short(coin, address)
    if coin.segwit and msg.script_type == InputScriptType.SPENDWITNESS:
        address_qr = address.upper()  # bech32 address
    elif coin.cashaddr_prefix is not None:
        address_qr = address.upper()  # cashaddr address
    else:
        address_qr = address  # base58 address

    if msg.multisig:
        multisig_xpub_magic = coin.xpub_magic
        if coin.segwit and not msg.ignore_xpub_magic:
            if (
                msg.script_type == InputScriptType.SPENDWITNESS
                and coin.xpub_magic_multisig_segwit_native is not None
            ):
                multisig_xpub_magic = coin.xpub_magic_multisig_segwit_native
            elif (
                msg.script_type == InputScriptType.SPENDP2SHWITNESS
                and coin.xpub_magic_multisig_segwit_p2sh is not None
            ):
                multisig_xpub_magic = coin.xpub_magic_multisig_segwit_p2sh

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
                if await show_xpubs(
                    ctx, coin, multisig_xpub_magic, pubnodes, multisig_index
                ):
                    break
        else:
            desc = address_n_to_str(msg.address_n)
            while True:
                if await show_address(ctx, address_short, desc=desc):
                    break
                if await show_qr(ctx, address_qr, desc=desc):
                    break

    return Address(address=address)
