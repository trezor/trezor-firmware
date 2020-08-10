from trezor import log, wire
from trezor.messages.CardanoAddress import CardanoAddress

from apps.common import paths
from apps.common.layout import address_n_to_str, show_qr

from . import CURVE, seed
from .address import derive_human_readable_address, validate_full_path
from .helpers import protocol_magics, staking_use_cases
from .helpers.utils import to_account_path
from .layout import (
    show_address,
    show_warning_address_foreign_staking_key,
    show_warning_address_pointer,
)

if False:
    from trezor.messages import CardanoAddressParametersType, CardanoGetAddress


@seed.with_keychain
async def get_address(
    ctx: wire.Context, msg: CardanoGetAddress, keychain: seed.Keychain
) -> CardanoAddress:
    address_parameters = msg.address_parameters

    await paths.validate_path(
        ctx, validate_full_path, keychain, address_parameters.address_n, CURVE
    )

    try:
        address = derive_human_readable_address(
            keychain, address_parameters, msg.protocol_magic, msg.network_id
        )
    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Deriving address failed")

    if msg.show_display:
        await _display_address(
            ctx, keychain, address_parameters, address, msg.protocol_magic
        )

    return CardanoAddress(address=address)


async def _display_address(
    ctx: wire.Context,
    keychain: seed.Keychain,
    address_parameters: CardanoAddressParametersType,
    address: str,
    protocol_magic: int,
) -> None:
    await _show_staking_warnings(ctx, keychain, address_parameters)

    network = None
    if not protocol_magics.is_mainnet(protocol_magic):
        network = protocol_magic

    while True:
        if await show_address(
            ctx,
            address,
            address_parameters.address_type,
            address_parameters.address_n,
            network=network,
        ):
            break
        if await show_qr(
            ctx, address, desc=address_n_to_str(address_parameters.address_n)
        ):
            break


async def _show_staking_warnings(
    ctx: wire.Context,
    keychain: seed.Keychain,
    address_parameters: CardanoAddressParametersType,
) -> None:
    staking_type = staking_use_cases.get(keychain, address_parameters)
    if staking_type == staking_use_cases.MISMATCH:
        await show_warning_address_foreign_staking_key(
            ctx,
            to_account_path(address_parameters.address_n),
            to_account_path(address_parameters.address_n_staking),
            address_parameters.staking_key_hash,
        )
    elif staking_type == staking_use_cases.POINTER_ADDRESS:
        await show_warning_address_pointer(ctx, address_parameters.certificate_pointer)
