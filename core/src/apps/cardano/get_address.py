from trezor import log, messages, wire

from . import addresses, seed
from .helpers.credential import Credential, should_show_credentials
from .helpers.utils import validate_network_info
from .layout import show_cardano_address, show_credentials


@seed.with_keychain
async def get_address(
    ctx: wire.Context, msg: messages.CardanoGetAddress, keychain: seed.Keychain
) -> messages.CardanoAddress:
    validate_network_info(msg.network_id, msg.protocol_magic)
    addresses.validate_address_parameters(msg.address_parameters)

    try:
        address = addresses.derive_human_readable(
            keychain, msg.address_parameters, msg.protocol_magic, msg.network_id
        )
    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Deriving address failed")

    if msg.show_display:
        await _display_address(ctx, msg.address_parameters, address, msg.protocol_magic)

    return messages.CardanoAddress(address=address)


async def _display_address(
    ctx: wire.Context,
    address_parameters: messages.CardanoAddressParametersType,
    address: str,
    protocol_magic: int,
) -> None:
    if should_show_credentials(address_parameters):
        await show_credentials(
            ctx,
            Credential.payment_credential(address_parameters),
            Credential.stake_credential(address_parameters),
        )

    await show_cardano_address(ctx, address_parameters, address, protocol_magic)
