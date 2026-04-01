if __debug__:
    from ubinascii import unhexlify

    from trezor.messages import EthereumTokenInfo

    # Stablecoin Yielding Vaults
    # Each entry: (vault_address, owner_name, asset_decimals, asset_identifier, chain_id)
    # Will be a list of tuples for each chain/network.
    KNOWN_VAULT = (
        unhexlify("Ac8C6e8779Dddc60F5cEF7701DcE70eCBa5ef518"),  # vault contract address
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
