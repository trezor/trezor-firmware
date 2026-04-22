from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from buffer_types import AnyBytes

from trezor.messages import EthereumNetworkInfo, EthereumTokenInfo

# Stablecoin Yielding Vaults
# Will be a list of tuples for each chain/network.
KNOWN_VAULT = (
    # Test vault: https://etherscan.io/address/0xa511d618cD0F9d7cAD791009d7c5E3b19c9568da
    b"\xa5\x11\xd6\x18\xcd\x0f\x9d\x7c\xad\x79\x10\x09\xd7\xc5\xe3\xb1\x9c\x95\x68\xda",  # vault contract address
    1,  # chain id (Ethereum)
    "Test Steakhouse USDC Prime Vault",  # owner/protocol name
    # Asset Token
    EthereumTokenInfo(
        symbol="USDC",
        decimals=6,
        address=b"\xa0\xb8\x69\x91\xc6\x21\x8b\x36\xc1\xd1\x9d\x4a\x2e\x9e\xb0\xce\x36\x06\xeb\x48",
        chain_id=1,
        name="USD Coin",
    ),
    # Vault token
    EthereumTokenInfo(
        symbol="tstSHUSDCp",
        decimals=18,
        address=b"\xa5\x11\xd6\x18\xcd\x0f\x9d\x7c\xad\x79\x10\x09\xd7\xc5\xe3\xb1\x9c\x95\x68\xda",  # vault contract address
        chain_id=1,
        name="Test Steakhouse USDC Prime",
    ),
)


def lookup_vault(
    network: EthereumNetworkInfo, vault_addr: AnyBytes
) -> tuple[bool, str, EthereumTokenInfo, EthereumTokenInfo]:
    """returns (is_known_vault, vault_name_or_address, asset_token, vault_token)"""
    from .helpers import address_from_bytes
    from .tokens import UNKNOWN_TOKEN

    if network.chain_id == KNOWN_VAULT[1] and vault_addr == KNOWN_VAULT[0]:
        return True, KNOWN_VAULT[2], KNOWN_VAULT[3], KNOWN_VAULT[4]
    else:
        return (
            False,
            address_from_bytes(vault_addr, network),
            UNKNOWN_TOKEN,
            UNKNOWN_TOKEN,
        )
