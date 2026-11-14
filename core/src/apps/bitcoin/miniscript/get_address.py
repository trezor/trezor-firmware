from typing import TYPE_CHECKING

from apps.ward import WardApp, with_ward

from ..keychain import with_keychain
from ..miniscript import derive_node

if TYPE_CHECKING:
    from trezor.messages import (
        Address,
        MiniscriptGetAddress,
    )

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain
    from apps.ward import WardStore


@with_keychain
@with_ward(WardApp.BITCOIN)
async def get_address(
    msg: MiniscriptGetAddress, keychain: Keychain, coin: CoinInfo, ward: WardStore
) -> Address:
    from trezor import TR
    from trezor.messages import Address
    from trezor.ui.layouts import (
        show_address,
    )

    from . import load_policy

    # TODO: validate with keychain
    # if msg.show_display:
    #     # skip soft-validation for silent calls
    #     # await validate_path(...)

    registered = await load_policy(ward, coin, msg.policy)  # must be registered
    address = registered.address_wsh(msg.derivation, coin)
    xpubs = [
        derive_node(key).serialize_public(coin.xpub_magic)
        for key in registered.policy.keys
    ]

    if msg.show_display:
        subtitle = TR.address__coin_address_template.format(coin.coin_shortcut)
        # TODO: also safety_checks? warn about miniscript?
        await show_address(
            address=address,
            subtitle=subtitle,
            case_sensitive=False,
            xpubs=xpubs,
            multisig_index=registered.policy.own_index,
            account=registered.info.name,
            chunkify=bool(msg.chunkify),
        )

    return Address(address=address)
