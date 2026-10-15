from typing import TYPE_CHECKING

from trezor.crypto.miniscript import compile
from trezor.protobuf import dump_message_buffer
from trezor.wire import DataError

from .keychain import with_keychain

if TYPE_CHECKING:
    from trezor.messages import (
        MiniscriptPolicy,
        MiniscriptRedeemPolicyType,
        MiniscriptRegisterPolicy,
        Success,
    )

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain


def derive_miniscript(derivation: MiniscriptRedeemPolicyType) -> bytes:
    from storage.device import get_registered_miniscript

    if get_registered_miniscript() == dump_message_buffer(derivation.policy):
        return compile(derivation)

    from trezor.wire import ProcessError

    raise ProcessError("Unregistered policy")


async def derive_xpubs(
    policy: MiniscriptPolicy, coin: CoinInfo
) -> list[tuple[bool, str]]:
    from trezor.crypto.miniscript import parse_node

    from ..common.keychain import get_keychain
    from ..common.paths import AlwaysMatchingSchema

    xpub_magic = coin.xpub_magic

    # TODO: use Miniscript-specific schema (also in GetAddress & SignTx)
    keychain = await get_keychain(coin.curve_name, [AlwaysMatchingSchema])
    root_fingerprint = keychain.root_fingerprint()

    result = []
    for key in policy.keys:
        # make sure provided node can be parsed and serialized
        key_xpub = parse_node(key.node).serialize_public(xpub_magic)
        is_ours = False
        if (fpr := key.root_fingerprint) is not None and fpr == root_fingerprint:
            our_xpub = keychain.derive(key.derivation_path).serialize_public(xpub_magic)
            is_ours = our_xpub == key_xpub
        result.append((is_ours, key_xpub))

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
    if not (name := policy.name):
        raise DataError("Empty name")

    # TODO: verify that descriptor should match coin - i.e. xpub-vs-tpub, no altcoin support?

    # Make sure the policy is valid and can be compiled into a script, before user confirmation
    # (derive first external & internal addresses)
    try:
        compile(MiniscriptRedeemPolicyType(policy=policy, internal=False, index=0))
        compile(MiniscriptRedeemPolicyType(policy=policy, internal=True, index=0))
    except ValueError:
        raise DataError("Invalid policy")

    derived: list[tuple[bool, str]] = await derive_xpubs(policy, coin)
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
    set_registered_miniscript(dump_message_buffer(policy))
    show_continue_in_app("Policy registered")
    return Success()
