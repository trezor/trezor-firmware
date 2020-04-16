from ubinascii import hexlify

from trezor import log, wire
from trezor.messages import CardanoAddressType
from trezor.messages.CardanoAddress import CardanoAddress
from trezor.messages.CardanoAddressParametersType import CardanoAddressParametersType

from apps.cardano import CURVE, seed
from apps.cardano.address import (
    derive_address,
    get_staking_key_hash,
    validate_full_path,
)
from apps.cardano.layout import (
    show_address,
    show_pointer_address_warning,
    show_staking_key_warnings,
)
from apps.common import paths
from apps.common.layout import address_n_to_str, show_qr

if False:
    from trezor.messages.CardanoGetAddress import CardanoGetAddress


@seed.with_keychains
async def get_address(
    ctx: wire.Context, msg: CardanoGetAddress, keychains: seed.Keychains
) -> CardanoAddress:
    address_parameters = msg.address_parameters

    await paths.validate_path(
        ctx, validate_full_path, keychains, address_parameters.address_n, CURVE
    )

    try:
        address = derive_address(keychains, address_parameters, msg.network_id)
    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Deriving address failed")

    if msg.show_display:
        await _display_address(ctx, address_parameters, keychains, address)

    return CardanoAddress(address=address)


async def _display_address(
    ctx: wire.Context,
    address_parameters: CardanoAddressParametersType,
    keychains: seed.Keychains,
    address: str,
) -> None:
    await _show_warnings_if_applicable(ctx, address_parameters, keychains)

    desc = address_n_to_str(address_parameters.address_n)
    while True:
        if await show_address(ctx, address, desc=desc):
            break
        if await show_qr(ctx, address, desc=desc):
            break


async def _show_warnings_if_applicable(
    ctx: wire.Context,
    address_parameters: CardanoAddressParametersType,
    keychains: seed.Keychains,
):
    if address_parameters.staking_key_hash is not None:
        account_staking_key_hash = get_staking_key_hash(
            keychains, address_parameters.address_n
        )
        if address_parameters.staking_key_hash != account_staking_key_hash:
            hash_str = hexlify(address_parameters.staking_key_hash).decode()
            account_path = address_n_to_str(address_parameters.address_n[:3])
            await show_staking_key_warnings(ctx, hash_str, account_path)
    elif address_parameters.address_type == CardanoAddressType.POINTER_ADDRESS:
        await show_pointer_address_warning(ctx, address_parameters.certificate_pointer)
