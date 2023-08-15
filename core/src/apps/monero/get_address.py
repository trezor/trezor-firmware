from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import MoneroAddress, MoneroGetAddress

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def get_address(msg: MoneroGetAddress, keychain: Keychain) -> MoneroAddress:
    from trezor import wire
    from trezor.messages import MoneroAddress
    from trezor.ui.layouts import show_address

    from apps.common import paths
    from apps.monero import misc
    from apps.monero.xmr import addresses, crypto_helpers, monero
    from apps.monero.xmr.networks import net_version

    account = msg.account  # local_cache_attribute
    minor = msg.minor  # local_cache_attribute
    payment_id = msg.payment_id  # local_cache_attribute

    await paths.validate_path(keychain, msg.address_n)

    creds = misc.get_creds(keychain, msg.address_n, msg.network_type)
    addr = creds.address

    have_subaddress = (
        account is not None and minor is not None and (account, minor) != (0, 0)
    )
    have_payment_id = payment_id is not None

    if (account is None) != (minor is None):
        raise wire.ProcessError("Invalid subaddress indexes")

    if have_payment_id and have_subaddress:
        raise wire.DataError("Subaddress cannot be integrated")

    if have_payment_id:
        assert payment_id is not None
        if len(payment_id) != 8:
            raise ValueError("Invalid payment ID length")
        addr = addresses.encode_addr(
            net_version(msg.network_type, False, True),
            crypto_helpers.encodepoint(creds.spend_key_public),
            crypto_helpers.encodepoint(creds.view_key_public),
            payment_id,
        )

    if have_subaddress:
        assert account is not None
        assert minor is not None

        pub_spend, pub_view = monero.generate_sub_address_keys(
            creds.view_key_private, creds.spend_key_public, account, minor
        )

        addr = addresses.encode_addr(
            net_version(msg.network_type, True, False),
            crypto_helpers.encodepoint(pub_spend),
            crypto_helpers.encodepoint(pub_view),
        )

    if msg.show_display:
        await show_address(
            addr,
            address_qr="monero:" + addr,
            path=paths.address_n_to_str(msg.address_n),
        )

    return MoneroAddress(address=addr.encode())
