from trezor.messages.MoneroAddress import MoneroAddress

from apps.common.layout import show_address, show_qr
from apps.monero import misc


async def get_address(ctx, msg):
    creds = await misc.get_creds(ctx, msg.address_n, msg.network_type)

    if msg.show_display:
        while True:
            if await show_address(ctx, creds.address.decode("ascii"), msg.address_n):
                break
            if await show_qr(ctx, creds.address.decode("ascii")):
                break

    return MoneroAddress(address=creds.address)
