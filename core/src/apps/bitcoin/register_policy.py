from typing import TYPE_CHECKING

from .keychain import with_keychain

if TYPE_CHECKING:
    from trezor.messages import Policy, RegisterPolicy

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain


@with_keychain
async def register_policy(msg: RegisterPolicy, keychain: Keychain, coin: CoinInfo) -> Policy:
    from trezor import TR
    from trezor.messages import Policy
    from trezor.ui.layouts import (
        confirm_action,
    )

    from apps.common.address_mac import get_policy_mac
    from apps.common.paths import address_n_to_str, validate_path

    from . import addresses
    from .keychain import (
        address_n_to_name_or_unknown,
        validate_path_against_script_type,
    )
    from .multisig import multisig_xpub_index

    address_n = msg.address_n  # local_cache_attribute

    node = keychain.derive(address_n)

    await confirm_action("register_policy", "Register policy", action=msg.script, subtitle=f"Policy name: {msg.name}")

    mac = get_policy_mac(msg.name, msg.script, coin.slip44, address_n, keychain)

    return Policy(mac=mac)
