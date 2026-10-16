from typing import TYPE_CHECKING

from trezor.crypto.miniscript import compile_internal
from trezor.protobuf import dump_message_buffer
from trezor.wire import DataError

from .keychain import with_keychain

if TYPE_CHECKING:
    from trezor.messages import (
        MiniscriptPolicy,
        MiniscriptRegisterPolicy,
        Success,
    )

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain


async def derive_xpubs(
    policy: MiniscriptPolicy,
    keychain: Keychain,
    xpub_magic: int,
) -> list[tuple[bool, str]]:
    from trezor.crypto.miniscript import derive_node

    root_fingerprint = keychain.root_fingerprint()

    child_path = [0, 0]  # change=0, index=0
    result = []
    for key in policy.keys:
        # make sure provided node can be parsed and derived
        key_xpub = derive_node(key.node, *child_path).serialize_public(xpub_magic)
        is_ours = False
        if (fpr := key.root_fingerprint) is not None and fpr == root_fingerprint:
            # will raise if this path is underivable on this device
            is_ours = keychain.derive(key.derivation_path + child_path).serialize_public(xpub_magic) == key_xpub
        result.append((is_ours, key_xpub))

    if not any(is_ours for is_ours, _ in result):
        raise DataError("No keys owned by this device")

    return result


@with_keychain
async def register_policy(
    msg: MiniscriptRegisterPolicy, keychain: Keychain, coin: CoinInfo
) -> Success:
    from storage.device import set_registered_miniscript
    from trezor import TR
    from trezor.messages import MiniscriptRedeemPolicyType, Success
    from trezor.ui.layouts import confirm_properties, show_continue_in_app

    policy = msg.policy

    # TODO: avoid similar names
    if not (name := msg.name):
        raise DataError("Empty name")

    # TODO: verify that descriptor should match coin - i.e. xpub-vs-tpub, no altcoin support?

    # Make sure the policy is valid and can be compiled into a script, before user confirmation
    # (derive first external & internal addresses)
    try:
        compile_internal(
            MiniscriptRedeemPolicyType(policy=policy, internal=False, index=0)
        )
        compile_internal(
            MiniscriptRedeemPolicyType(policy=policy, internal=True, index=0)
        )
    except ValueError:
        raise DataError("Invalid policy")

    # Miniscript is using descriptors with xpub/tpubs:
    derived = await derive_xpubs(policy, keychain, coin.xpub_magic)
    await confirm_properties(
        title=f"Register {coin.coin_name} Miniscript policy?",
        subtitle=name,
        props=[(None, policy.descriptor, True)],
        br_name="register_policy",
    )
    for i, (is_ours, xpub) in enumerate(derived):
        await confirm_properties(
            title=f"Key @{i} {TR.address__title_yours if is_ours else TR.address__title_cosigner}",
            subtitle=name,
            props=[(None, xpub, True)],
            br_name="register_policy",
        )

    # TODO: segregate registration per coin
    # TODO: canonicalize policy (e.g. @K ordering)
    from trezor.crypto.hashlib import sha256

    digest = sha256(dump_message_buffer(policy)).digest()
    set_registered_miniscript(digest)
    show_continue_in_app("Policy registered")
    return Success()
