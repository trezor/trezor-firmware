from trezor.messages.VsysAddress import VsysAddress

from apps.common import paths, seed
from apps.common.layout import address_n_to_str, show_address, show_qr
from apps.vsys import CURVE, helpers
from apps.vsys.constants import ACCOUNT_API_VER, PROTOCOL, OPC_ACCOUNT


async def get_address(ctx, msg, keychain):
    await paths.validate_path(
        ctx, helpers.validate_full_path, keychain, msg.address_n, CURVE
    )

    node = keychain.derive(msg.address_n, CURVE)

    pk = seed.remove_ed25519_prefix(node.public_key())
    chain_id = helpers.get_chain_id(msg.address_n)
    address = helpers.get_address_from_public_key(pk, chain_id)

    if msg.show_display:
        desc = address_n_to_str(msg.address_n)
        while True:
            if await show_address(ctx, address, desc=desc):
                break
            if await show_qr(ctx, address, desc=desc):
                break

    return VsysAddress(api=ACCOUNT_API_VER, address=address, protocol=PROTOCOL, opc=OPC_ACCOUNT)
