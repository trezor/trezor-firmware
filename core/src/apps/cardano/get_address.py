from typing import TYPE_CHECKING

from . import seed

if TYPE_CHECKING:
    from trezor.messages import CardanoAddress, CardanoGetAddress
    from trezor.wire import MaybeEarlyResponse


@seed.with_keychain
async def get_address(
    msg: CardanoGetAddress, keychain: seed.Keychain
) -> MaybeEarlyResponse[CardanoAddress]:
    from trezor import log, wire
    from trezor.messages import CardanoAddress
    from trezor.ui.layouts import show_continue_in_app
    from trezor.wire import early_response

    from . import addresses
    from .helpers.credential import Credential, should_show_credentials
    from .helpers.utils import validate_network_info
    from .layout import show_cardano_address, show_credentials

    address_parameters = msg.address_parameters  # local_cache_attribute

    validate_network_info(msg.network_id, msg.protocol_magic)
    addresses.validate_address_parameters(address_parameters)

    try:
        address = addresses.derive_human_readable(
            keychain, address_parameters, msg.protocol_magic, msg.network_id
        )
    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Deriving address failed")

    response = CardanoAddress(address=address)

    if msg.show_display:
        from trezor import TR

        # _display_address
        if should_show_credentials(address_parameters):
            await show_credentials(
                Credential.payment_credential(address_parameters),
                Credential.stake_credential(address_parameters),
            )
        await show_cardano_address(
            address_parameters, address, msg.protocol_magic, chunkify=bool(msg.chunkify)
        )
        return await early_response(
            response, show_continue_in_app(TR.address__confirmed)
        )

    return response
