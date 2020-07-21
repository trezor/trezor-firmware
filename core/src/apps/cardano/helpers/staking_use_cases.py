from trezor.messages import CardanoAddressType

from ..address import get_public_key_hash

if False:
    from typing import List
    from trezor.messages import CardanoAddressParametersType
    from . import seed


"""
Used as a helper when deciding what warnings we should
display to the user during get_address and sign_tx depending
on the type of address and its parameters.
"""


NO_STAKING = 0
SAME_ACCOUNT = 1
SAME_HASH = 2
DIFFERENT_ACCOUNT = 3
DIFFERENT_HASH = 4
POINTER_ADDRESS = 5
REWARD_ADDRESS = 6


def get(
    keychain: seed.Keychain, address_parameters: CardanoAddressParametersType
) -> int:
    address_type = address_parameters.address_type
    if address_type == CardanoAddressType.BASE:
        spending_account_staking_path = _path_to_staking_path(
            address_parameters.address_n
        )
        if address_parameters.address_n_staking:
            if address_parameters.address_n_staking != spending_account_staking_path:
                return DIFFERENT_ACCOUNT
            else:
                return SAME_ACCOUNT
        else:
            staking_key_hash = get_public_key_hash(
                keychain, spending_account_staking_path
            )
            if address_parameters.staking_key_hash != staking_key_hash:
                return DIFFERENT_HASH
            else:
                return SAME_HASH
    elif address_type == CardanoAddressType.POINTER:
        return POINTER_ADDRESS
    elif address_type == CardanoAddressType.REWARD:
        return REWARD_ADDRESS
    else:
        return NO_STAKING


def _path_to_staking_path(path: List[int]) -> List[int]:
    return path[:3] + [2, 0]
