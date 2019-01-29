from trezor import log, wire
from trezor.messages.CardanoAddress import CardanoAddress

from apps.cardano import seed
from apps.cardano.address import derive_address_and_node, validate_full_path
from apps.common import paths
from apps.common.layout import address_n_to_str, show_address, show_qr


async def get_address(ctx, msg):
    keychain = await seed.get_keychain(ctx)

    await paths.validate_path(ctx, validate_full_path, path=msg.address_n)

    try:
        address, _ = derive_address_and_node(keychain, msg.address_n)
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
