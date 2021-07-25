from trezor.enums import CardanoAddressType

from ..address import get_public_key_hash
from ..seed import is_shelley_path
from .utils import to_account_path

if False:
    from trezor.messages import CardanoAddressParametersType
    from ..seed import Keychain


"""
Used as a helper when deciding what warnings we should
display to the user during get_address and sign_tx depending
on the type of address and its parameters.
"""


NO_STAKING = 0
MATCH = 1
MISMATCH = 2
POINTER_ADDRESS = 3


def get(keychain: Keychain, address_parameters: CardanoAddressParametersType) -> int:
    address_type = address_parameters.address_type
    if address_type == CardanoAddressType.BASE:
        if not is_shelley_path(address_parameters.address_n):
            return MISMATCH

        spending_account_staking_path = _path_to_staking_path(
            address_parameters.address_n
        )
        if address_parameters.address_n_staking:
            if address_parameters.address_n_staking != spending_account_staking_path:
                return MISMATCH
        else:
            staking_key_hash = get_public_key_hash(
                keychain, spending_account_staking_path
            )
            if address_parameters.staking_key_hash != staking_key_hash:
                return MISMATCH

        return MATCH
    elif address_type == CardanoAddressType.POINTER:
        return POINTER_ADDRESS
    elif address_type == CardanoAddressType.REWARD:
        return MATCH
    else:
        return NO_STAKING


def _path_to_staking_path(path: list[int]) -> list[int]:
    return to_account_path(path) + [2, 0]
