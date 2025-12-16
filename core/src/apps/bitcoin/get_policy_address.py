from typing import TYPE_CHECKING

from .keychain import with_keychain

if TYPE_CHECKING:
    from trezor.messages import Address, GetPolicyAddress

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain


@with_keychain
async def get_policy_address(
    msg: GetPolicyAddress, keychain: Keychain, coin: CoinInfo
) -> Address:
    from trezor import protobuf
    from trezor.crypto import hmac
    from trezor.messages import Address
    from trezor.ui.layouts import show_address
    from trezor.wire import DataError

    key = keychain.derive_slip21([b"SLIP-0019", b"Trezor-Policy"]).key()

    new_buffer = bytearray(protobuf.encoded_length(msg.policy))
    protobuf.encode(new_buffer, msg.policy)
    encoded_policy = bytes(new_buffer)
    policy_mac = hmac(hmac.SHA256, key, encoded_policy).digest()

    if policy_mac != msg.mac:
        raise DataError("Invalid MAC")

    address = "TODO"

    return Address(address=address)
