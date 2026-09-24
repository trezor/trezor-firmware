from typing import TYPE_CHECKING

from trezor.wire import DataError, ProcessError

if TYPE_CHECKING:
    from trezor.messages import MiniscriptPolicy, MiniscriptRegisterPolicy, Success

    from apps.common.paths import Bip32Path


def _derive_miniscript_unchecked(
    policy: MiniscriptPolicy, address_n: Bip32Path
) -> bytes:
    from trezorminiscript import compile

    change, index = address_n[-2:]
    internal = bool(change & 1)  # TODO: Liana change index convention

    return compile(policy.descriptor, internal, index)


def derive_miniscript(
    policy: MiniscriptPolicy,
    address_n: Bip32Path,
) -> bytes:
    from storage.device import get_registered_miniscript
    from trezor.protobuf import dump_message_buffer

    if get_registered_miniscript() == dump_message_buffer(policy):
        return _derive_miniscript_unchecked(policy, address_n)

    raise ProcessError("Unregistered descriptor")


async def register_policy(msg: MiniscriptRegisterPolicy) -> Success:
    from storage.device import set_registered_miniscript
    from trezor.messages import Success
    from trezor.protobuf import dump_message_buffer
    from trezor.ui.layouts import confirm_value, show_continue_in_app

    policy = msg.policy
    if not policy.descriptor:
        raise DataError("Empty descriptor")

    name = msg.name
    if not name:
        raise DataError("Empty name")

    # TODO: verify that descriptor should match coin - i.e. xpub-vs-tpub, no altcoin support?

    # Make sure the policy is valid and can be compiled into a script, before user confirmation
    # (derive first external address: internal=0, index=0)
    _derive_miniscript_unchecked(policy, [0, 0])

    # TODO: segregate registration per coin
    await confirm_value(
        title="Register policy?",
        value=policy.descriptor,
        description=name,
        br_name="/bitcoin/miniscript/register_policy",
    )

    set_registered_miniscript(dump_message_buffer(policy))
    show_continue_in_app("Policy registered")
    return Success()
