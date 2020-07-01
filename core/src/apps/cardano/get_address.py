from trezor import log, wire
from trezor.messages.CardanoAddress import CardanoAddress

from apps.common import paths
from apps.common.layout import address_n_to_str, show_address, show_qr

from . import CURVE, seed
from .address import derive_address_and_node, validate_full_path


@seed.with_keychain
async def get_address(ctx, msg, keychain: seed.Keychain):
    await paths.validate_path(ctx, validate_full_path, keychain, msg.address_n, CURVE)

    try:
        address, _ = derive_address_and_node(
            keychain, msg.address_n, msg.protocol_magic
        )
    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Deriving address failed")
    if msg.show_display:
        desc = address_n_to_str(msg.address_n)
        while True:
            if await show_address(ctx, address, desc=desc):
                break
            if await show_qr(ctx, address, desc=desc):
                break

    return CardanoAddress(address=address)
