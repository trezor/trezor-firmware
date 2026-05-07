from typing import TYPE_CHECKING

from trezor.wire import DataError

from .keychain import with_keychain

if TYPE_CHECKING:
    from trezor.messages import Policy, RegisteredPolicy

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain
    from apps.common.paths import Bip32Path


def policy_hmac(msg: Policy, keychain: Keychain) -> bytes:
    from trezor import protobuf
    from trezor.crypto import hmac

    key = keychain.derive_slip21([b"SLIP-0019", b"Trezor Miniscript Policy"]).key()

    new_buffer = bytearray(protobuf.encoded_length(msg))
    protobuf.encode(new_buffer, msg)
    encoded_policy = bytes(new_buffer)
    return hmac(hmac.SHA256, key, encoded_policy).digest()


def get_descriptor(msg: Policy) -> str:
    res = msg.template
    if len(msg.xpubs) > 10:
        raise DataError("Too many xpubs")

    for i, xpub in enumerate(msg.xpubs):
        res = res.replace(f"@{i}", xpub)

    return res.replace("/**", "/<0;1>/*")


def _derive_miniscript_unchecked(
    policy: Policy, coin: CoinInfo, address_n: Bip32Path
) -> bytes:
    if coin.coin_name != policy.coin_name:
        raise DataError("Invalid coin name")

    from trezorminiscript import compile

    # TODO: check change sanity?
    change, index = address_n[-2:]

    return compile(get_descriptor(policy), change, index)


def derive_miniscript(
    msg: RegisteredPolicy,
    keychain: Keychain,
    coin: CoinInfo,
    address_n: Bip32Path,
) -> bytes:

    if policy_hmac(msg.policy, keychain) == msg.mac:
        return _derive_miniscript_unchecked(msg.policy, coin, address_n)

    raise DataError("Unregistered policy")


@with_keychain
async def register_policy(
    msg: Policy, keychain: Keychain, coin: CoinInfo
) -> RegisteredPolicy:
    from trezor.messages import RegisteredPolicy
    from trezor.ui.layouts import confirm_value, show_continue_in_app

    if not msg.template:
        raise DataError("No descriptor")

    if not msg.name:
        raise DataError("No name")

    # Make sure the policy is valid and can be compiled into a script, before user confirmation
    # (derive first external address: change=0, index=0)
    _derive_miniscript_unchecked(msg, coin, [0, 0])

    await confirm_value(
        title=f"Register {msg.coin_name} policy",
        value=msg.template,
        description=msg.name,
        br_name="/bitcoin/miniscript/register_policy",
    )

    for i, xpub in enumerate(msg.xpubs):
        await confirm_value(
            title=f"Public key #{i}",
            value=xpub,
            description="",
            br_name="/bitcoin/miniscript/register_policy",
        )

    show_continue_in_app("Policy registered")

    return RegisteredPolicy(policy=msg, mac=policy_hmac(msg, keychain))
