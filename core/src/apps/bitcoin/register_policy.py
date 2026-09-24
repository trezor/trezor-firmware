from typing import TYPE_CHECKING

from trezor.crypto.miniscript import compile

from .keychain import with_keychain

if TYPE_CHECKING:
    from trezor.messages import (
        MiniscriptRedeemPolicyType,
        MiniscriptRegisterPolicy,
        Success,
    )

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain


def derive_miniscript(derivation: MiniscriptRedeemPolicyType) -> bytes:
    from storage.device import get_registered_miniscript
    from trezor.protobuf import dump_message_buffer

    if get_registered_miniscript() == dump_message_buffer(derivation.policy):
        return compile(derivation)

    from trezor.wire import ProcessError

    raise ProcessError("Unregistered policy")


@with_keychain
async def register_policy(
    msg: MiniscriptRegisterPolicy, keychain: Keychain, coin: CoinInfo
) -> Success:
    from storage.device import set_registered_miniscript
    from trezor.crypto.miniscript import parse_nodes
    from trezor.messages import MiniscriptRedeemPolicyType, Success
    from trezor.protobuf import dump_message_buffer
    from trezor.ui.layouts import confirm_properties, show_continue_in_app
    from trezor.wire import DataError

    policy = msg.policy
    if not policy.descriptor:
        raise DataError("Empty descriptor")

    name = msg.name
    if not name:
        raise DataError("Empty name")

    # TODO: verify that descriptor should match coin - i.e. xpub-vs-tpub, no altcoin support?

    # Make sure the policy is valid and can be compiled into a script, before user confirmation
    # (derive first external & internal addresses)
    try:
        compile(MiniscriptRedeemPolicyType(policy=policy, internal=False, index=0))
        compile(MiniscriptRedeemPolicyType(policy=policy, internal=True, index=0))
    except ValueError:
        raise DataError("Invalid policy")

    # TODO: segregate registration per coin
    # TODO: mark our xpub(s)

    nodes = parse_nodes(policy.nodes)
    props = [(name, policy.descriptor, True)]
    for i, node in enumerate(nodes):
        xpub = node.serialize_public(coin.xpub_magic)
        props.append((f"Key @{i}", xpub, True))

    await confirm_properties(
        title="Register policy?",
        props=props,
        br_name="/bitcoin/miniscript/register_policy",
    )

    set_registered_miniscript(dump_message_buffer(policy))
    show_continue_in_app("Policy registered")
    return Success()
