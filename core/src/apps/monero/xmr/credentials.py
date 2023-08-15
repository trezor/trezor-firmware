from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.enums import MoneroNetworkType

    from apps.monero.xmr import crypto


class AccountCreds:
    """
    Stores account private keys
    """

    def __init__(
        self,
        view_key_private: crypto.Scalar,
        spend_key_private: crypto.Scalar,
        view_key_public: crypto.Point,
        spend_key_public: crypto.Point,
        address: str,
        network_type: MoneroNetworkType,
    ) -> None:
        self.view_key_private = view_key_private
        self.view_key_public = view_key_public
        self.spend_key_private = spend_key_private
        self.spend_key_public = spend_key_public
        self.address: str | None = address
        self.network_type: MoneroNetworkType | None = network_type

    @classmethod
    def new_wallet(
        cls,
        priv_view_key: crypto.Scalar,
        priv_spend_key: crypto.Scalar,
        network_type: MoneroNetworkType | None = None,
    ) -> "AccountCreds":
        from trezor.enums import MoneroNetworkType

        from apps.monero.xmr import crypto, crypto_helpers
        from apps.monero.xmr.addresses import encode_addr
        from apps.monero.xmr.networks import net_version

        if network_type is None:
            network_type = MoneroNetworkType.MAINNET

        pub_view_key = crypto.scalarmult_base_into(None, priv_view_key)
        pub_spend_key = crypto.scalarmult_base_into(None, priv_spend_key)
        addr = encode_addr(
            net_version(network_type),
            crypto_helpers.encodepoint(pub_spend_key),
            crypto_helpers.encodepoint(pub_view_key),
        )
        return cls(
            priv_view_key,
            priv_spend_key,
            pub_view_key,
            pub_spend_key,
            addr,
            network_type,
        )
