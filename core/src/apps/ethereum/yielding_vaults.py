if __debug__:
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from buffer_types import AnyBytes

    from trezor.messages import EthereumNetworkInfo, EthereumTokenInfo

    # Stablecoin Yielding Vaults
    # Each entry: (vault_address, owner_name, asset_decimals, asset_identifier, chain_id)
    # Will be a list of tuples for each chain/network.
    KNOWN_VAULT = (
        b"\xac\x8c\x6e\x87\x79\xdd\xdc\x60\xf5\xce\xf7\x70\x1d\xce\x70\xec\xba\x5e\xf5\x18",  # vault contract address
        8453,  # chain id (Base)
        "Trezor Test Vault (Base)",  # owner/protocol name
        EthereumTokenInfo(
            symbol="USDC",
            decimals=6,
            address=b"\xa0\xb8\x69\x91\xc6\x21\x8b\x36\xc1\xd1\x9d\x4a\x2e\x9e\xb0\xce\x36\x06\xeb\x48",
            chain_id=8453,
            name="USD Coin",
        ),
    )

    def lookup_vault(
        vault_addr: AnyBytes, network: EthereumNetworkInfo
    ) -> tuple[str, EthereumTokenInfo]:
        from .helpers import address_from_bytes
        from .tokens import UNKNOWN_TOKEN

        if vault_addr == KNOWN_VAULT[0] and network.chain_id == KNOWN_VAULT[1]:
            return KNOWN_VAULT[2], KNOWN_VAULT[3]
        else:
            return address_from_bytes(vault_addr, network), UNKNOWN_TOKEN
