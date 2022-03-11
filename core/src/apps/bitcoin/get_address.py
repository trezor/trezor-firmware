from typing import TYPE_CHECKING

from trezor.crypto import bip32
from trezor.enums import InputScriptType
from trezor.messages import Address
from trezor.ui.layouts import show_address

from apps.common.address_mac import get_address_mac
from apps.common.paths import address_n_to_str, validate_path

from . import addresses
from .keychain import validate_path_against_script_type, with_keychain
from .multisig import multisig_pubkey_index

if TYPE_CHECKING:
    from trezor.messages import GetAddress
    from trezor.messages import HDNodeType
    from trezor import wire
    from apps.common.keychain import Keychain
    from apps.common.coininfo import CoinInfo


def _get_xpubs(
    coin: CoinInfo, xpub_magic: int, pubnodes: list[HDNodeType]
) -> list[str]:
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
        result.append(node.serialize_public(xpub_magic))

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

    address_case_sensitive = True
    if coin.segwit and msg.script_type in (
        InputScriptType.SPENDWITNESS,
        InputScriptType.SPENDTAPROOT,
    ):
        address_case_sensitive = False  # bech32 address
    elif coin.cashaddr_prefix is not None:
        address_case_sensitive = False  # cashaddr address

    mac: bytes | None = None
    multisig_xpub_magic = coin.xpub_magic
    if msg.multisig:
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
    else:
        # Attach a MAC for single-sig addresses, but only if the path is standard
        # or if the user explicitly confirms a non-standard path.
        if msg.show_display or (
            keychain.is_in_keychain(msg.address_n)
            and validate_path_against_script_type(coin, msg)
        ):
            mac = get_address_mac(address, coin.slip44, keychain)

    if msg.show_display:
        if msg.multisig:
            if msg.multisig.nodes:
                pubnodes = msg.multisig.nodes
            else:
                pubnodes = [hd.node for hd in msg.multisig.pubkeys]
            multisig_index = multisig_pubkey_index(msg.multisig, node.public_key())

            title = f"Multisig {msg.multisig.m} of {len(pubnodes)}"
            await show_address(
                ctx,
                address=address_short,
                case_sensitive=address_case_sensitive,
                title=title,
                multisig_index=multisig_index,
                xpubs=_get_xpubs(coin, multisig_xpub_magic, pubnodes),
            )
        else:
            title = address_n_to_str(msg.address_n)
            await show_address(
                ctx,
                address=address_short,
                address_qr=address,
                case_sensitive=address_case_sensitive,
                title=title,
            )

    return Address(address=address, mac=mac)
