from typing import TYPE_CHECKING

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERNS, SLIP44_ID

if TYPE_CHECKING:
    from trezor.messages import NEMAddress, NEMGetAddress
    from trezor.wire import MaybeEarlyResponse

    from apps.common.keychain import Keychain


@with_slip44_keychain(*PATTERNS, slip44_id=SLIP44_ID, curve=CURVE)
async def get_address(
    msg: NEMGetAddress, keychain: Keychain
) -> MaybeEarlyResponse[NEMAddress]:
    from trezor.messages import NEMAddress
    from trezor.ui.layouts import show_address, show_continue_in_app
    from trezor.wire import early_response

    from apps.common import paths

    from .helpers import check_path, get_network_str
    from .validators import validate_network

    address_n = msg.address_n  # local_cache_attribute
    network = msg.network  # local_cache_attribute

    validate_network(network)
    await paths.validate_path(keychain, address_n, check_path(address_n, network))

    node = keychain.derive(address_n)
    address = node.nem_address(network)
    response = NEMAddress(address=address)

    if msg.show_display:
        from trezor import TR

        from . import PATTERNS, SLIP44_ID

        await show_address(
            address,
            case_sensitive=False,
            path=paths.address_n_to_str(address_n),
            account=paths.get_account_name("NEM", msg.address_n, PATTERNS, SLIP44_ID),
            network=get_network_str(network),
            chunkify=bool(msg.chunkify),
        )
        return await early_response(
            response, show_continue_in_app(TR.address__confirmed)
        )

    return response
