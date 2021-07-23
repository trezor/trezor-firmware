from trezor import log, wire
from trezor.messages import CardanoAddress

from . import seed
from .address import derive_human_readable_address, validate_address_parameters
from .helpers.credential import Credential, should_show_address_credentials
from .layout import show_cardano_address, show_credentials
from .sign_tx import validate_network_info

if False:
    from trezor.messages import (
        CardanoAddressParametersType,
        CardanoGetAddress,
    )


@seed.with_keychain
async def get_address(
    ctx: wire.Context, msg: CardanoGetAddress, keychain: seed.Keychain
) -> CardanoAddress:
    address_parameters = msg.address_parameters

    validate_network_info(msg.network_id, msg.protocol_magic)
    validate_address_parameters(address_parameters)

    try:
        address = derive_human_readable_address(
            keychain, address_parameters, msg.protocol_magic, msg.network_id
        )
    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Deriving address failed")

    if msg.show_display:
        await _display_address(ctx, address_parameters, address, msg.protocol_magic)

    return CardanoAddress(address=address)


async def _display_address(
    ctx: wire.Context,
    address_parameters: CardanoAddressParametersType,
    address: str,
    protocol_magic: int,
) -> None:
    if should_show_address_credentials(address_parameters):
        await show_credentials(
            ctx,
            Credential.payment_credential(address_parameters),
            Credential.stake_credential(address_parameters),
        )

    await show_cardano_address(ctx, address_parameters, address, protocol_magic)
