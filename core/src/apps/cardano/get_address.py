from typing import TYPE_CHECKING

from . import seed

if TYPE_CHECKING:
    from trezor.wire import Context
    from trezor.messages import CardanoGetAddress, CardanoAddress


@seed.with_keychain
async def get_address(
    ctx: Context, msg: CardanoGetAddress, keychain: seed.Keychain
) -> CardanoAddress:
    from trezor.messages import CardanoAddress
    from trezor import log, wire
    from .helpers.credential import Credential, should_show_credentials
    from .helpers.utils import validate_network_info
    from .layout import show_cardano_address, show_credentials
    from . import addresses

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

    if msg.show_display:
        # _display_address
        if should_show_credentials(address_parameters):
            await show_credentials(
                ctx,
                Credential.payment_credential(address_parameters),
                Credential.stake_credential(address_parameters),
            )
        await show_cardano_address(ctx, address_parameters, address, msg.protocol_magic)

    return CardanoAddress(address=address)
