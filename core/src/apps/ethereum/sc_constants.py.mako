# generated from ${THIS_FILE.name}
# (by running `make templates` in `core`)
# do not edit manually!
# fmt: off

from typing import Iterator
<%
from binascii import unhexlify

def fmt_addr(addr_hex: str) -> str:
    data = "".join(f'\\x{b:02x}' for b in unhexlify(addr_hex))
    return f'b"{data}"'


KNOWN_ADDRESSES = [
    # https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/1inch/calldata-AggregationRouterV6.json#L9
    (1, "111111125421cA6dc452d289314280a0f8842A65", "1inch Aggregation Router V6"),
    # https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/lifi/calldata-LIFIDiamond.json
    (1, "1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE", "LiFI Diamond"),
    # https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/uniswap/calldata-UniswapV3Router02.json#L6
    (1, "68b3465833fb72A70ecDF485E0e4C7bD8665Fc45", "Uniswap V3 Router"),
    # https://etherscan.io/address/0xe592427a0aece92de3edee1f18e0157c05861564
    (1, "e592427a0aece92de3edee1f18e0157c05861564", "Uniswap V3 Router"),
    # Lido
    # https://etherscan.io/address/0x889edc2edab5f40e902b864ad4d7ade8e412f9b1
    (1, "889edc2edab5f40e902b864ad4d7ade8e412f9b1", "Lido"),
    # https://etherscan.io/address/0xae7ab96520de3a18e5e111b5eaab095312d7fe84
    (1, "ae7ab96520de3a18e5e111b5eaab095312d7fe84", "Lido"),
    # https://etherscan.io/address/0xa88f0329c2c4ce51ba3fc619bbf44efe7120dd0d
    (1, "a88f0329c2c4ce51ba3fc619bbf44efe7120dd0d", "Lido"),
    # https://etherscan.io/address/0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0
    (1, "7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0", "Lido"),
    # Morpho
    # https://etherscan.io/address/0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb
    (1, "bbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb", "Morpho"),
    # https://basescan.org/address/0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb
    (8453, "bbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb", "Morpho"),
    # https://etherscan.io/address/0x6566194141eefa99af43bb5aa71460ca2dc90245
    (1, "6566194141eefa99af43bb5aa71460ca2dc90245", "Morpho"),
    # https://basescan.org/address/0x6bfd8137e702540e7a42b74178a4a49ba43920c4
    (8453, "6bfd8137e702540e7a42b74178a4a49ba43920c4", "Morpho"),
    # Kiln
    # https://etherscan.io/address/0x576834cb068e677db4aff6ca245c7bde16c3867e
    (1, "576834cb068e677db4aff6ca245c7bde16c3867e", "Kiln"),
    # https://etherscan.io/address/0x004c226fff73aa94b78a4df1a0e861797ba16819
    (1, "004c226fff73aa94b78a4df1a0e861797ba16819", "Kiln"),
    # Missing account tag on ethscan. But contract deployer is tagged as Kiln.
    # Fresh high value transactions.
    # https://etherscan.io/address/0x8659eeff31cfcff580d37af8e7af250f8998aa83
    (1, "8659eeff31cfcff580d37af8e7af250f8998aa83", "Kiln"),
    # Ethena
    # https://etherscan.io/address/0x9d39a5de30e57443bff2a8307a4256c8797a3497
    (1, "9d39a5de30e57443bff2a8307a4256c8797a3497", "Ethena"),
    # StarkGate
    # https://etherscan.io/address/0xce5485cfb26914c5dce00b9baf0580364dafc7a4
    (1, "ce5485cfb26914c5dce00b9baf0580364dafc7a4", "StarkGate"),
    # WalletConnect
    # https://optimistic.etherscan.io/address/0x521b4c065bbdbe3e20b3727340730936912dfa46
    (10, "521b4c065bbdbe3e20b3727340730936912dfa46", "WalletConnect"),
    # https://optimistic.etherscan.io/address/0xef4461891dfb3ac8572ccf7c794664a8dd927945
    (10, "ef4461891dfb3ac8572ccf7c794664a8dd927945", "WalletConnect"),
    # https://etherscan.io/address/0xef4461891dfb3ac8572ccf7c794664a8dd927945
    (1, "ef4461891dfb3ac8572ccf7c794664a8dd927945", "WalletConnect"),
    # https://basescan.org/address/0xef4461891dfb3ac8572ccf7c794664a8dd927945
    (8453, "ef4461891dfb3ac8572ccf7c794664a8dd927945", "WalletConnect"),
    # Core Stake
    # https://scan.coredao.org/address/0x0000000000000000000000000000000000001011
    (1116, "0000000000000000000000000000000000001011", "Core Stake"),
    # https://scan.coredao.org/address/0x0000000000000000000000000000000000001010
    (1116, "0000000000000000000000000000000000001010", "Core Stake"),
    # yield.xyz
    # https://etherscan.io/address/0xb929b89153fc2eed442e81e5a1add4e2fa39028f
    (1, "b929b89153fc2eed442e81e5a1add4e2fa39028f", "yield.xyz"),
    # https://etherscan.io/address/0x56d783ca8e0b998c57a428bf1c26a8baca50524e
    (1, "56d783ca8e0b998c57a428bf1c26a8baca50524e", "yield.xyz"),
    # https://etherscan.io/address/0x857679d69fe50e7b722f94acd2629d80c355163d
    (1, "857679d69fe50e7b722f94acd2629d80c355163d", "yield.xyz"),
    # https://etherscan.io/address/0xf30cf4ed712d3734161fdaab5b1dbb49fd2d0e5c
    (1, "f30cf4ed712d3734161fdaab5b1dbb49fd2d0e5c", "yield.xyz"),
    # https://etherscan.io/address/0x5a10de50160126a5f936506bd342c541ac44e943
    (1, "5a10de50160126a5f936506bd342c541ac44e943", "yield.xyz"),
    # https://etherscan.io/address/0x35b1ca0f398905cf752e6fe122b51c88022fca32
    (1, "35b1ca0f398905cf752e6fe122b51c88022fca32", "yield.xyz"),
    # https://etherscan.io/address/0xd9e6987d77bf2c6d0647b8181fd68a259f838c36
    (1, "d9e6987d77bf2c6d0647b8181fd68a259f838c36", "yield.xyz"),
    # https://etherscan.io/address/0xd14a87025109013b0a2354a775cb335f926af65a
    (1, "d14a87025109013b0a2354a775cb335f926af65a", "yield.xyz"),
    # https://etherscan.io/address/0xa6e768fef2d1af36c0cfdb276422e7881a83e951
    (1, "a6e768fef2d1af36c0cfdb276422e7881a83e951", "yield.xyz"),
    # https://etherscan.io/address/0x467585aaea860f9d8b3b43bb994e4da8a93788a7
    (1, "467585aaea860f9d8b3b43bb994e4da8a93788a7", "yield.xyz"),
    # https://etherscan.io/address/0x06998af8f39ff8630d1fb515d22781da4dc2ca71
    (1, "06998af8f39ff8630d1fb515d22781da4dc2ca71", "yield.xyz"),
    # https://etherscan.io/address/0x875e901465a639f2e71fcfc10f426ed32f5a909a
    (1, "875e901465a639f2e71fcfc10f426ed32f5a909a", "yield.xyz"),
    # https://etherscan.io/address/0x2905b3387c9550ea57fa3ee7d4b7e5abf3acd3d2
    (1, "2905b3387c9550ea57fa3ee7d4b7e5abf3acd3d2", "yield.xyz"),
    # https://etherscan.io/address/0x15c2b3adca66e26b6f230b4023f52a285b7f9995
    (1, "15c2b3adca66e26b6f230b4023f52a285b7f9995", "yield.xyz"),
]

# Canonical WETH (Wrapped Ether) contracts holding the chain's native currency.
WETH_DEPLOYMENTS = [
    # https://etherscan.io/address/0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2
    (1, "C02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),
    # https://optimistic.etherscan.io/address/0x4200000000000000000000000000000000000006
    (10, "4200000000000000000000000000000000000006"),
    # https://arbiscan.io/address/0x82aF49447D8a07e3bd95BD0d56f35241523fBab1
    (42161, "82aF49447D8a07e3bd95BD0d56f35241523fBab1"),
    # https://basescan.org/address/0x4200000000000000000000000000000000000006
    (8453, "4200000000000000000000000000000000000006"),
    # https://sepolia.etherscan.io/address/0x7b79995e5f793A07Bc00c21412e50Ecae098E7f9
    (11155111, "7b79995e5f793A07Bc00c21412e50Ecae098E7f9"),
    # https://holesky.etherscan.io/address/0x94373a4919B3240D86eA41593D5eBa789FEF3848
    (17000, "94373a4919B3240D86eA41593D5eBa789FEF3848"),
]

%>

def lookup_known_address(chain_id: int, address: bytes) -> str | None:
    """Return a human-readable name of a well-known smart contract,
    or `None` if the address is not known.
    """
    for known_chain_id, known_address, name in _known_address_iterator():
        if chain_id == known_chain_id and address == known_address:
            return name
    return None


def _known_address_iterator() -> Iterator[tuple[int, bytes, str]]:
    # NOTE: implementing the `_known_address_iterator` as a generator instead of an if-tree of `return` statements saves flash size (Same trick as in `apps.ethereum.tokens`.)

% for chain_id, addr, name in KNOWN_ADDRESSES:
    yield (${chain_id}, ${fmt_addr(addr)}, "${name}")
% endfor
    for chain_id, addr in weth_deployments():
        yield (chain_id, addr, "WETH")

    if __debug__:
        yield (1, ${fmt_addr("dddddddddddddddddddddddddddddddddddddddd")}, "Trezor Test. DO NOT USE")


def weth_deployments() -> Iterator[tuple[int, bytes]]:
    """Canonical WETH (Wrapped Ether) contract deployments: (chain_id, address)."""
% for chain_id, addr in WETH_DEPLOYMENTS:
    yield (${chain_id}, ${fmt_addr(addr)})
% endfor
