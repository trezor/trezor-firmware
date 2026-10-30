from typing import TYPE_CHECKING

from trezor.wire import DataError

from ..keychain import with_keychain
from ..sign_tx.layout import address_n_to_str
from . import derive_node, store_policy, validate_policy

if TYPE_CHECKING:
    from trezor.messages import (
        MiniscriptRegisterPolicy,
        Success,
    )

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain


@with_keychain
async def register_policy(
    msg: MiniscriptRegisterPolicy, keychain: Keychain, coin: CoinInfo
) -> Success:
    from trezor import TR
    from trezor.messages import (
        Success,
    )
    from trezor.ui.layouts import confirm_properties, show_continue_in_app

    policy = msg.policy

    # TODO: avoid similar names
    if not (name := msg.name):
        raise DataError("Empty name")

    # TODO: verify that descriptor should match coin - no altcoin support?
    validate_policy(policy, keychain, coin)

    # TODO: Make sure the policy is valid and can be compiled into a script, before user confirmation (derive first external & internal addresses)

    # Miniscript is using descriptors with xpub/tpubs:
    await confirm_properties(
        title=f"{coin.coin_name} policy",
        subtitle=name,
        props=[(None, policy.descriptor, True)],
        br_name="register_policy",
    )
    for i, key in enumerate(policy.keys):
        fpr = key.root_fingerprint
        origin = address_n_to_str(key.derivation_path, prefix=f"{fpr:08x}")
        xpub = derive_node(key).serialize_public(coin.xpub_magic)

        if i == policy.own_index:
            label = TR.address__title_yours
        else:
            label = TR.address__title_cosigner
        await confirm_properties(
            title=f"Key @{i} {label}",
            subtitle=origin,
            props=[(None, xpub, True)],
            br_name="register_policy",
        )

    # TODO: segregate registration per coin
    await store_policy(policy, name)
    show_continue_in_app("Policy registered")
    return Success()
