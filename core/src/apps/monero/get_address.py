from typing import TYPE_CHECKING

from trezor import wire
from trezor.messages import MoneroAddress
from trezor.ui.layouts import show_address

from apps.common import paths
from apps.common.keychain import auto_keychain
from apps.monero import misc
from apps.monero.xmr import addresses, crypto, monero
from apps.monero.xmr.networks import net_version

if TYPE_CHECKING:
    from trezor.messages import MoneroGetAddress

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def get_address(
    ctx: wire.Context, msg: MoneroGetAddress, keychain: Keychain
) -> MoneroAddress:
    await paths.validate_path(ctx, keychain, msg.address_n)

    creds = misc.get_creds(keychain, msg.address_n, msg.network_type)
    addr = creds.address

    have_subaddress = msg.account is not None and msg.minor is not None
    have_payment_id = msg.payment_id is not None

    if (msg.account is None) != (msg.minor is None):
        raise wire.ProcessError("Invalid subaddress indexes")

    if have_payment_id and have_subaddress:
        raise wire.DataError("Subaddress cannot be integrated")

    if have_payment_id:
        assert msg.payment_id is not None
        if len(msg.payment_id) != 8:
            raise ValueError("Invalid payment ID length")
        addr = addresses.encode_addr(
            net_version(msg.network_type, False, True),
            crypto.encodepoint(creds.spend_key_public),
            crypto.encodepoint(creds.view_key_public),
            msg.payment_id,
        )

    if have_subaddress:
        assert msg.account is not None
        assert msg.minor is not None

        pub_spend, pub_view = monero.generate_sub_address_keys(
            creds.view_key_private, creds.spend_key_public, msg.account, msg.minor
        )

        addr = addresses.encode_addr(
            net_version(msg.network_type, True, False),
            crypto.encodepoint(pub_spend),
            crypto.encodepoint(pub_view),
        )

    if msg.show_display:
        title = paths.address_n_to_str(msg.address_n)
        await show_address(
            ctx,
            address=addr,
            address_qr="monero:" + addr,
            title=title,
        )

    return MoneroAddress(address=addr.encode())
