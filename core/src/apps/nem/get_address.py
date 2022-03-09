from typing import TYPE_CHECKING

from trezor.messages import NEMAddress
from trezor.ui.layouts import show_address

from apps.common.keychain import with_slip44_keychain
from apps.common.paths import address_n_to_str, validate_path

from . import CURVE, PATTERNS, SLIP44_ID
from .helpers import check_path, get_network_str
from .validators import validate_network

if TYPE_CHECKING:
    from apps.common.keychain import Keychain
    from trezor.wire import Context
    from trezor.messages import NEMGetAddress


@with_slip44_keychain(*PATTERNS, slip44_id=SLIP44_ID, curve=CURVE)
async def get_address(
    ctx: Context, msg: NEMGetAddress, keychain: Keychain
) -> NEMAddress:
    validate_network(msg.network)
    await validate_path(
        ctx, keychain, msg.address_n, check_path(msg.address_n, msg.network)
    )

    node = keychain.derive(msg.address_n)
    address = node.nem_address(msg.network)

    if msg.show_display:
        title = address_n_to_str(msg.address_n)
        await show_address(
            ctx,
            address=address,
            case_sensitive=False,
            title=title,
            network=get_network_str(msg.network),
        )

    return NEMAddress(address=address)
