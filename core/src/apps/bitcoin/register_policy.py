from typing import TYPE_CHECKING

from trezor.wire import DataError, ProcessError

from .keychain import with_keychain

if TYPE_CHECKING:
    from trezor.messages import MiniscriptDescriptor, Success

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain
    from apps.common.paths import Bip32Path


def get_descriptor(msg: MiniscriptDescriptor) -> str:
    return msg.descriptor


def _derive_miniscript_unchecked(
    miniscript: MiniscriptDescriptor, coin: CoinInfo, address_n: Bip32Path
) -> bytes:
    if coin.coin_name != miniscript.coin_name:
        raise DataError("Invalid coin name")

    from trezorminiscript import compile

    change, index = address_n[-2:]
    internal = bool(change & 1)  # TODO: Liana change index convention

    return compile(get_descriptor(miniscript), internal, index)


def derive_miniscript(
    msg: MiniscriptDescriptor,
    coin: CoinInfo,
    address_n: Bip32Path,
) -> bytes:
    from storage.device import get_registered_miniscript
    from trezor.protobuf import dump_message_buffer

    if get_registered_miniscript() == dump_message_buffer(msg):
        return _derive_miniscript_unchecked(msg, coin, address_n)

    raise ProcessError("Unregistered descriptor")


@with_keychain
async def register_policy(
    msg: MiniscriptDescriptor, _keychain: Keychain, coin: CoinInfo
) -> Success:
    from storage.device import set_registered_miniscript
    from trezor.messages import Success
    from trezor.protobuf import dump_message_buffer
    from trezor.ui.layouts import confirm_value, show_continue_in_app

    if not msg.descriptor:
        raise DataError("No descriptor")

    if not msg.name:
        raise DataError("No name")

    # Make sure the policy is valid and can be compiled into a script, before user confirmation
    # (derive first external address: internal=0, index=0)
    _derive_miniscript_unchecked(msg, coin, [0, 0])

    await confirm_value(
        title=f"Register {msg.coin_name} policy",
        value=msg.descriptor,
        description=msg.name,
        br_name="/bitcoin/miniscript/register_policy",
    )

    set_registered_miniscript(dump_message_buffer(msg))
    show_continue_in_app("Policy registered")
    return Success()
