from trezor.crypto import bip32
from trezor.messages import InputScriptType
from trezor.messages.Address import Address
from trezor.ui.layouts import show_address

from apps.common.layout import address_n_to_str
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


def _get_xpubs(coin: CoinInfo, pubnodes: List[HDNodeType]) -> List[str]:
    result = []
    for pubnode in pubnodes:
        node = bip32.HDNode(
            depth=pubnode.depth,
            fingerprint=pubnode.fingerprint,
            child_num=pubnode.child_num,
            chain_code=pubnode.chain_code,
            public_key=pubnode.public_key,
            curve_name=coin.curve_name,
        )
        result.append(node.serialize_public(coin.xpub_magic))

    return result


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
            await show_address(
                ctx,
                address=address_short,
                address_qr=address_qr,
                desc=desc,
                multisig_index=multisig_index,
                xpubs=_get_xpubs(coin, pubnodes),
            )
        else:
            desc = address_n_to_str(msg.address_n)
            await show_address(
                ctx, address=address_short, address_qr=address_qr, desc=desc
            )

    return Address(address=address)
