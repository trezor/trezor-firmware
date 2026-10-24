from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import MoneroAddress, MoneroGetAddress

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def get_address(msg: MoneroGetAddress, keychain: Keychain) -> MoneroAddress:
    from trezor import TR, wire
    from trezor.messages import MoneroAddress
    from trezor.ui.layouts import show_address

    from apps.common import paths
    from apps.monero.xmr import addresses, crypto
    from apps.monero.xmr.networks import net_version

    account = msg.account  # local_cache_attribute
    minor = msg.minor  # local_cache_attribute
    payment_id = msg.payment_id  # local_cache_attribute
    address_n = msg.address_n  # local_cache_attribute

    await paths.validate_path(keychain, address_n)

    have_subaddress = (
        account is not None and minor is not None and (account, minor) != (0, 0)
    )
    have_payment_id = payment_id is not None

    if (account is None) != (minor is None):
        raise wire.ProcessError("Invalid subaddress indexes")

    if have_payment_id and have_subaddress:
        raise wire.DataError("Subaddress cannot be integrated")

    if have_payment_id and len(payment_id) != 8:
        raise ValueError("Invalid payment ID length")

    node = keychain.derive(address_n)
    public_spend, public_view, _ = crypto.wallet_public(node, account or 0, minor or 0)
    address = addresses.encode_addr(
        net_version(msg.network_type, have_subaddress, have_payment_id),
        public_spend,
        public_view,
        payment_id if have_payment_id else None,
    )

    if msg.show_display:
        from . import PATTERN, SLIP44_ID

        coin = "XMR"
        await show_address(
            address,
            subtitle=TR.address__coin_address_template.format(coin),
            address_qr="monero:" + address,
            path=paths.address_n_to_str(address_n),
            account=paths.get_account_name(coin, msg.address_n, PATTERN, SLIP44_ID),
            chunkify=bool(msg.chunkify),
        )

    return MoneroAddress(address=address.encode())
