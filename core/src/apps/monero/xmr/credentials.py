from typing import TYPE_CHECKING

from trezor.enums import MoneroNetworkType

from apps.monero.xmr import crypto
from apps.monero.xmr.addresses import encode_addr
from apps.monero.xmr.networks import net_version

if TYPE_CHECKING:
    from .crypto import Sc25519, Ge25519


class AccountCreds:
    """
    Stores account private keys
    """

    def __init__(
        self,
        view_key_private: Sc25519,
        spend_key_private: Sc25519,
        view_key_public: Ge25519,
        spend_key_public: Ge25519,
        address: str,
        network_type: MoneroNetworkType,
    ) -> None:
        self.view_key_private = view_key_private
        self.view_key_public = view_key_public
        self.spend_key_private = spend_key_private
        self.spend_key_public = spend_key_public
        self.address = address
        self.network_type = network_type

    @classmethod
    def new_wallet(
        cls,
        priv_view_key: Sc25519,
        priv_spend_key: Sc25519,
        network_type: MoneroNetworkType = MoneroNetworkType.MAINNET,
    ) -> "AccountCreds":
        pub_view_key = crypto.scalarmult_base(priv_view_key)
        pub_spend_key = crypto.scalarmult_base(priv_spend_key)
        addr = encode_addr(
            net_version(network_type),
            crypto.encodepoint(pub_spend_key),
            crypto.encodepoint(pub_view_key),
        )
        return cls(
            view_key_private=priv_view_key,
            spend_key_private=priv_spend_key,
            view_key_public=pub_view_key,
            spend_key_public=pub_spend_key,
            address=addr,
            network_type=network_type,
        )
