from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import DarkfiAddress, DarkfiGetAddress


async def get_address(msg: DarkfiGetAddress) -> DarkfiAddress:
    from ubinascii import hexlify

    from trezor.crypto import pallas
    from trezor.messages import DarkfiAddress

    from . import account_spend_key

    sk = await account_spend_key(msg.account)
    # pk_d = ivk * NullifierK, where ivk is derived from the FVK (ak, nk).
    ivk = pallas.derive_ivk(sk)
    pk_d = pallas.address_pubkey(ivk)

    if msg.show_display:
        from trezor import TR
        from trezor.ui.layouts import show_address

        # The canonical bs58check address string is assembled host-side (it needs
        # BLAKE3, which is not in device firmware); we show the raw pk_d here.
        pk_d_hex = hexlify(pk_d).decode()
        await show_address(
            pk_d_hex,
            subtitle=TR.address__coin_address_template.format("DRK"),
            chunkify=bool(msg.chunkify),
        )

    return DarkfiAddress(pk_d=pk_d)
