from typing import TYPE_CHECKING

from ..keychain import with_keychain

if TYPE_CHECKING:
    from trezor.messages import (
        Address,
        MiniscriptGetAddress,
    )

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain


@with_keychain
async def get_address(
    msg: MiniscriptGetAddress, keychain: Keychain, coin: CoinInfo
) -> Address:
    from trezor import TR
    from trezor.messages import Address
    from trezor.ui.layouts import (
        show_address,
    )

    from .. import addresses
    from . import load_policy

    # TODO: validate with keychain
    # if msg.show_display:
    #     # skip soft-validation for silent calls
    #     # await validate_path(
    #     #     keychain,
    #     #     address_n,
    #     #     validate_path_against_script_type(coin, msg),
    #     # )

    name = load_policy(msg.policy)  # must be registered
    address = addresses.address_miniscript(msg.policy, msg.derivation, coin)

    if msg.show_display:
        subtitle = TR.address__coin_address_template.format(coin.coin_shortcut)
        # TODO: also safety_checks? warn about miniscript?
        await show_address(
            address=address,
            subtitle=subtitle,
            case_sensitive=False,
            # TODO: add xpubs and origins
            account=name,
            chunkify=bool(msg.chunkify),
        )

    return Address(address=address)
