from ubinascii import unhexlify

# Stablecoin Yielding Vaults
# Each entry: (vault_address, owner_name, asset_decimals, asset_identifier, chain_id)
# Could later be a list of tuples for each chain/network.
VAULT_GAUNTLET_USDC = (
    unhexlify("BEEF01735c132Ada46AA9aA4c54623cAA92A64CB"),  # vault contract address
    "Gauntlet USDC",  # owner/protocol name
    6,  # USDC has 6 decimal places
    "USDC",  # underlying asset identifier
    1,  # chain id (1 for Ethereum mainnet)
)
