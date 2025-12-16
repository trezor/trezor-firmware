from typing import TYPE_CHECKING

from .keychain import with_keychain

if TYPE_CHECKING:
    from trezor.messages import PolicyRegistration, RegisterPolicy

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain


@with_keychain
async def register_policy(
    msg: RegisterPolicy, keychain: Keychain, coin: CoinInfo
) -> PolicyRegistration:
    from trezor import TR
    from trezor.messages import PolicyRegistration
    from trezor.ui.layouts import confirm_action, confirm_value

    from apps.common.address_mac import get_policy_mac

    await confirm_action(
        "Bitcoin/Miniscript/RegisterPolicy",
        "Inheritance wallet setup",
        action=f"Review and register the wallet's policy: {msg.name}",
        extra_menu_items=[("Wallet descriptor", msg.script)],
    )

    await confirm_value(
        "Primary key",
        msg.xpubs[0],
        "Allows for spending available funds at any time.",
        "Bitcoin/Miniscript/RegisterPolicy",
    )

    mac = get_policy_mac(
        msg.name, msg.script, msg.xpubs, msg.blocks, coin.slip44, keychain
    )

    return PolicyRegistration(mac=mac)
