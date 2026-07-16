from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from trezor.messages import EthereumNetworkInfo

    from .keychain import MsgInSignTx

from trezor.messages import EthereumTokenInfo

from .tokens import UNKNOWN_TOKEN

# Ethereum address bytes (20-byte)
_TEST_SH_USDC_VAULT_ADDRESS = (
    b"\xa5\x11\xd6\x18\xcd\x0f\x9d\x7c\xad\x79\x10\x09\xd7\xc5\xe3\xb1\x9c\x95\x68\xda"
)
_SH_USDC_VAULT_ADDRESS = (
    b"\xde\x6c\x23\xe5\x61\xf3\xe5\x58\x46\x20\x7e\xc4\x5a\x91\xb7\x77\xe0\xf7\xc8\x89"
)
_SH_USDT_VAULT_ADDRESS = (
    b"\xe4\xdb\x1c\x5a\x1b\x70\x9c\xe4\xd2\xad\xa6\x98\x5d\x9d\x50\x6e\x58\xf7\x38\x29"
)
_SH_ETH_VAULT_ADDRESS = (
    b"\x70\x4c\xfb\x08\x96\x90\x48\xa8\xdf\xf2\x98\xb2\x14\xf9\x59\x79\x1d\x8d\xa5\x09"
)
_USDC_ADDRESS = (
    b"\xa0\xb8\x69\x91\xc6\x21\x8b\x36\xc1\xd1\x9d\x4a\x2e\x9e\xb0\xce\x36\x06\xeb\x48"
)
_USDT_ADDRESS = (
    b"\xda\xc1\x7f\x95\x8d\x2e\xe5\x23\xa2\x20\x62\x06\x99\x45\x97\xc1\x3d\x83\x1e\xc7"
)
_WETH_ADDRESS = (
    b"\xc0\x2a\xaa\x39\xb2\x23\xfe\x8d\x0a\x0e\x5c\x4f\x27\xea\xd9\x08\x3c\x75\x6c\xc2"
)


class EthereumVaultInfo:
    def __init__(
        self,
        address: AnyBytes | None,
        chain_id: int | None,
        name: str,
        asset_token: EthereumTokenInfo,
        vault_token: EthereumTokenInfo,
    ) -> None:
        self.address = address
        self.chain_id = chain_id
        self.name = name
        self.asset_token = asset_token
        self.vault_token = vault_token


KNOWN_VAULTS = (
    # Test vault: https://etherscan.io/address/0xa511d618cD0F9d7cAD791009d7c5E3b19c9568da
    EthereumVaultInfo(
        address=_TEST_SH_USDC_VAULT_ADDRESS,
        chain_id=1,
        name="Test Steakhouse USDC Prime Vault",
        asset_token=EthereumTokenInfo(
            symbol="USDC",
            decimals=6,
            address=_USDC_ADDRESS,
            chain_id=1,
            name="USD Coin",
        ),
        vault_token=EthereumTokenInfo(
            symbol="tstSHUSDCp",
            decimals=18,
            address=_TEST_SH_USDC_VAULT_ADDRESS,
            chain_id=1,
            name="Test Steakhouse USDC Prime Vault",
        ),
    ),
    # https://etherscan.io/address/0xde6c23E561F3e55846207EC45A91b777e0F7C889
    EthereumVaultInfo(
        address=_SH_USDC_VAULT_ADDRESS,
        chain_id=1,
        name="Trezor Steakhouse USDC Prime Vault",
        asset_token=EthereumTokenInfo(
            symbol="USDC",
            decimals=6,
            address=_USDC_ADDRESS,
            chain_id=1,
            name="USD Coin",
        ),
        vault_token=EthereumTokenInfo(
            symbol="trSHUSDCp",
            decimals=18,
            address=_SH_USDC_VAULT_ADDRESS,
            chain_id=1,
            name="Trezor Steakhouse USDC Prime Vault",
        ),
    ),
    # https://etherscan.io/address/0xE4DB1c5A1B709CE4d2adA6985D9D506e58F73829
    EthereumVaultInfo(
        address=_SH_USDT_VAULT_ADDRESS,
        chain_id=1,
        name="Trezor Steakhouse USDT Prime Vault",
        asset_token=EthereumTokenInfo(
            symbol="USDT",
            decimals=6,
            address=_USDT_ADDRESS,
            chain_id=1,
            name="Tether USD",
        ),
        vault_token=EthereumTokenInfo(
            symbol="trSHUSDTp",
            decimals=18,
            address=_SH_USDT_VAULT_ADDRESS,
            chain_id=1,
            name="Trezor Steakhouse USDT Prime Vault",
        ),
    ),
    # https://etherscan.io/address/0x704cFb08969048a8DFf298B214F959791d8Da509
    EthereumVaultInfo(
        address=_SH_ETH_VAULT_ADDRESS,
        chain_id=1,
        name="Trezor Steakhouse ETH Prime Vault",
        asset_token=EthereumTokenInfo(
            symbol="WETH",
            decimals=18,
            address=_WETH_ADDRESS,
            chain_id=1,
            name="Wrapped Ether",
        ),
        vault_token=EthereumTokenInfo(
            symbol="trSHETHp",
            decimals=18,
            address=_SH_ETH_VAULT_ADDRESS,
            chain_id=1,
            name="Trezor Steakhouse ETH Prime Vault",
        ),
    ),
)

UNKNOWN_VAULT = EthereumVaultInfo(
    address=None,
    chain_id=None,
    name="UNKNOWN VAULT",
    asset_token=UNKNOWN_TOKEN,
    vault_token=UNKNOWN_TOKEN,
)


async def get_token_label(
    token_addr: AnyBytes,
    network: EthereumNetworkInfo,
    msg: MsgInSignTx,
    try_fetch_definitions: bool,
) -> str:
    # MORPHO is hardcoded. We support it regardless of Trezor Connect support.
    # https://etherscan.io/token/0x58d97b57bb95320f9a05dc918aef65434969c2b2
    _MORPHO_ADDR = b"\x58\xd9\x7b\x57\xbb\x95\x32\x0f\x9a\x05\xdc\x91\x8a\xef\x65\x43\x49\x69\xc2\xb2"
    if token_addr == _MORPHO_ADDR and network.chain_id == 1:
        return "MORPHO"

    if try_fetch_definitions and msg.supports_definition_request:
        from .clear_signing import request_definitions

        addr = bytes(token_addr)
        received_definitions, _ = await request_definitions(
            msg.chain_id, addr, func_sig=None
        )
        if received_definitions is not None:
            token = received_definitions.get_token(addr)
            if token is not UNKNOWN_TOKEN:
                return token.symbol

    return "UNKNOWN"


def lookup_vault(
    network: EthereumNetworkInfo, vault_addr: AnyBytes
) -> EthereumVaultInfo:
    """Returns the vault info for the given address and network"""

    for vault in KNOWN_VAULTS:
        if network.chain_id == vault.chain_id and vault_addr == vault.address:
            return vault

    return UNKNOWN_VAULT
