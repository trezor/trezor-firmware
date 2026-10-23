from typing import TYPE_CHECKING

from trezor.wire import DataError

from ..keychain import with_keychain
from ..sign_tx.layout import address_n_to_str
from . import derive_node, store_policy, validate_policy

if TYPE_CHECKING:
    from trezor.crypto import bip32
    from trezor.messages import (
        MiniscriptPolicy,
        MiniscriptRegisterPolicy,
        Success,
    )

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain


def derive_xpubs(
    policy: MiniscriptPolicy,
    keychain: Keychain,
    xpub_magic: int,
) -> list[tuple[bool, str, str]]:
    root_fingerprint = keychain.root_fingerprint()

    def _to_xpub(node: bip32.HDNode) -> str:
        return node.serialize_public(xpub_magic)

    children = [0, 0]  # first external address
    result = []
    for key in policy.keys:
        # make sure provided node can be parsed and derived
        key_xpub = _to_xpub(derive_node(key, *children))
        is_ours = False
        origin = "Unknown origin"
        if (fpr := key.root_fingerprint) == root_fingerprint:
            # TODO: will raise if this path is underivable on this device
            is_ours = (
                _to_xpub(keychain.derive(key.derivation_path + children)) == key_xpub
            )
            origin = address_n_to_str(key.derivation_path, prefix=f"{fpr:08x}")
        result.append((is_ours, origin, _to_xpub(derive_node(key))))

    if not any(is_ours for is_ours, *_ in result):
        raise DataError("No keys owned by this device")

    return result


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

    # TODO: verify that descriptor should match coin - i.e. xpub-vs-tpub, no altcoin support?
    validate_policy(policy, coin)

    # Make sure the policy is valid and can be compiled into a script, before user confirmation
    # (derive first external & internal addresses)

    # Miniscript is using descriptors with xpub/tpubs:
    derived = derive_xpubs(policy, keychain, coin.xpub_magic)
    await confirm_properties(
        title=f"{coin.coin_name} policy",
        subtitle=name,
        props=[(None, policy.descriptor, True)],
        br_name="register_policy",
    )
    for i, (is_ours, origin, xpub) in enumerate(derived):
        await confirm_properties(
            title=f"Key @{i} {TR.address__title_yours if is_ours else TR.address__title_cosigner}",
            subtitle=origin,
            props=[(None, xpub, True)],
            br_name="register_policy",
        )

    # TODO: segregate registration per coin
    store_policy(policy, name)
    show_continue_in_app("Policy registered")
    return Success()
