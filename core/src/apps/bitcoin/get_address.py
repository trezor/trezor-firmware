from typing import TYPE_CHECKING

from trezor.enums import MultisigPubkeysOrder

from apps.common import safety_checks

from .common import multisig_uses_single_path
from .keychain import with_keychain

if TYPE_CHECKING:
    from trezor.messages import Address, GetAddress, HDNodeType

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain


def _get_xpubs(
    coin: CoinInfo, xpub_magic: int, pubnodes: list[HDNodeType]
) -> list[str]:
    from trezor.crypto import bip32

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
async def get_address(msg: GetAddress, keychain: Keychain, coin: CoinInfo) -> Address:
    from trezor.enums import InputScriptType
    from trezor.messages import Address
    from trezor.ui.layouts import (
        confirm_multisig_different_paths_warning,
        confirm_multisig_warning,
        show_address,
    )

    from apps.common.address_mac import get_address_mac
    from apps.common.paths import address_n_to_str, validate_path

    from . import addresses
    from .keychain import (
        address_n_to_name_or_unknown,
        validate_path_against_script_type,
    )
    from .multisig import multisig_xpub_index

    multisig = msg.multisig  # local_cache_attribute
    address_n = msg.address_n  # local_cache_attribute
    script_type = msg.script_type  # local_cache_attribute

    if msg.show_display:
        # skip soft-validation for silent calls
        await validate_path(
            keychain,
            address_n,
            validate_path_against_script_type(coin, msg),
        )

    node = keychain.derive(address_n)

    address = addresses.get_address(script_type, coin, node, multisig)
    address_short = addresses.address_short(coin, address)

    address_case_sensitive = True
    if coin.segwit and script_type in (
        InputScriptType.SPENDWITNESS,
        InputScriptType.SPENDTAPROOT,
    ):
        address_case_sensitive = False  # bech32 address
    elif coin.cashaddr_prefix is not None:
        address_case_sensitive = False  # cashaddr address

    mac: bytes | None = None
    multisig_xpub_magic = coin.xpub_magic
    if multisig:
        if coin.segwit and not msg.ignore_xpub_magic:
            if (
                script_type == InputScriptType.SPENDWITNESS
                and coin.xpub_magic_multisig_segwit_native is not None
            ):
                multisig_xpub_magic = coin.xpub_magic_multisig_segwit_native
            elif (
                script_type == InputScriptType.SPENDP2SHWITNESS
                and coin.xpub_magic_multisig_segwit_p2sh is not None
            ):
                multisig_xpub_magic = coin.xpub_magic_multisig_segwit_p2sh
    else:
        # Attach a MAC for single-sig addresses, but only if the path is standard
        # or if the user explicitly confirms a non-standard path.
        if msg.show_display or (
            keychain.is_in_keychain(address_n)
            and validate_path_against_script_type(coin, msg)
        ):
            mac = get_address_mac(address, coin.slip44, keychain)

    if msg.show_display:
        path = address_n_to_str(address_n)
        if multisig:
            if multisig.nodes:
                pubnodes = multisig.nodes
            else:
                pubnodes = [hd.node for hd in multisig.pubkeys]
            multisig_index = multisig_xpub_index(multisig, node.public_key())

            await confirm_multisig_warning()

            if not multisig_uses_single_path(multisig):
                # An address that uses different derivation paths for different xpubs
                # could be difficult to discover if the user did not note all the paths.
                # The reason is that each path ends with an address index, which can have
                # 1,000,000 possible values. If the address is a t-out-of-n multisig, the
                # total number of possible paths is 1,000,000^n. This can be exploited by
                # an attacker who has compromised the user's computer. The attacker could
                # randomize the address indices and then demand a ransom from the user to
                # reveal the paths. To prevent this, we require that all xpubs use the
                # same derivation path.
                if safety_checks.is_strict():
                    raise ValueError(
                        "Using different paths for different xpubs is not allowed"
                    )
                else:
                    await confirm_multisig_different_paths_warning()

            if multisig.pubkeys_order == MultisigPubkeysOrder.LEXICOGRAPHIC:
                account = f"Multisig {multisig.m} of {len(pubnodes)}\n(sorted)"
            else:
                account = f"Multisig {multisig.m} of {len(pubnodes)}"

            await show_address(
                address_short,
                case_sensitive=address_case_sensitive,
                path=path,
                multisig_index=multisig_index,
                xpubs=_get_xpubs(coin, multisig_xpub_magic, pubnodes),
                account=account,
                chunkify=bool(msg.chunkify),
            )
        else:
            account = address_n_to_name_or_unknown(coin, address_n, script_type)
            await show_address(
                address_short,
                address_qr=address,
                case_sensitive=address_case_sensitive,
                path=path,
                account=account,
                chunkify=bool(msg.chunkify),
            )

    return Address(address=address, mac=mac)
