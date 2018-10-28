from trezor.messages.MoneroAddress import MoneroAddress

from apps.common.layout import address_n_to_str, show_address, show_qr
from apps.monero import misc


async def get_address(ctx, msg):
    creds = await misc.get_creds(ctx, msg.address_n, msg.network_type)

    if msg.show_display:
        desc = address_n_to_str(msg.address_n)
        while True:
            if await show_address(ctx, creds.address.decode(), desc=desc):
                break
            if await show_qr(ctx, creds.address.decode(), desc=desc):
                break

    return MoneroAddress(address=creds.address)
