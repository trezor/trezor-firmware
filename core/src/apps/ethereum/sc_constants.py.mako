# generated from ${THIS_FILE.name}
# (by running `make templates` in `core`)
# do not edit manually!
# fmt: off

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
<%
def fmt_addr(addr_hex: str) -> str:
    data = "".join(f'\\x{b:02x}' for b in bytes.fromhex(addr_hex))
    return f'b"{data}"'

KNOWN_ADDRESSES = [
    # https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/uniswap/calldata-UniswapV3Router02.json#L6
    (1, "68b3465833fb72A70ecDF485E0e4C7bD8665Fc45", "Uniswap V3 Router"),
    # https://etherscan.io/address/0xe592427a0aece92de3edee1f18e0157c05861564
    (1, "e592427a0aece92de3edee1f18e0157c05861564", "Uniswap V3 Router"),
]

# (chain_id, address) pairs for ETH staking pool (stake/unstake) contracts.
STAKING_ADDRESSES_POOL = [
    # https://etherscan.io/address/0xd523794c879d9ec028960a231f866758e405be34
    (1, "d523794c879d9ec028960a231f866758e405be34"),  # mainnet
    # https://hoodi.etherscan.io/address/0xafa848357154a6a624686b348303ef9a13f63264
    (560048, "afa848357154a6a624686b348303ef9a13f63264"),  # Hoodi testnet
]

# (chain_id, address) pairs for ETH staking accounting (claim) contracts.
STAKING_ADDRESSES_ACCOUNTING = [
    # https://etherscan.io/address/0x7a7f0b3c23c23a31cfcb0c44709be70d4d545c6e
    (1, "7a7f0b3c23c23a31cfcb0c44709be70d4d545c6e"),  # mainnet
    # https://hoodi.etherscan.io/address/0x624087dd1904ab122a32878ce9e933c7071f53b9
    (560048, "624087dd1904ab122a32878ce9e933c7071f53b9"),  # Hoodi testnet
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


# TODO: We can update these addresses in the registry. With `Unwrap` also being added in this PR: https://github.com/ethereum/clear-signing-erc7730-registry/pull/3060
# We can get rid of the hardcoded addresses and formatters.
def weth_deployments() -> Iterator[tuple[int, bytes]]:
    """Canonical WETH (Wrapped Ether) contract deployments: (chain_id, address)."""
% for chain_id, addr in WETH_DEPLOYMENTS:
    yield (${chain_id}, ${fmt_addr(addr)})
% endfor


# (chain_id, address) pairs for ETH staking pool (stake/unstake) contracts.
STAKING_ADDRESSES_POOL = (
% for chain_id, addr in STAKING_ADDRESSES_POOL:
    (${chain_id}, ${fmt_addr(addr)}),
% endfor
)

# (chain_id, address) pairs for ETH staking accounting (claim) contracts.
STAKING_ADDRESSES_ACCOUNTING = (
% for chain_id, addr in STAKING_ADDRESSES_ACCOUNTING:
    (${chain_id}, ${fmt_addr(addr)}),
% endfor
)

<%
_EIP7702_ADDRESSES = {
    1: [  # Ethereum
        # https://etherscan.io/address/0x5a7fc11397e9a8ad41bf10bf13f22b0a63f96f6d
        ("5a7fc11397e9a8ad41bf10bf13f22b0a63f96f6d", "Ambire"),
        # https://etherscan.io/address/0x63c0c19a282a1b52b07dd5a65b58948a07dae32b
        ("63c0c19a282a1b52b07dd5a65b58948a07dae32b", "MetaMask"),
        # https://etherscan.io/address/0x4Cd241E8d1510e30b2076397afc7508Ae59C66c9
        ("4Cd241E8d1510e30b2076397afc7508Ae59C66c9", "Simple7702Account")
    ],
    10: [ # Optimism
        # https://explorer.optimism.io/address/0x4Cd241E8d1510e30b2076397afc7508Ae59C66c9
        ("4Cd241E8d1510e30b2076397afc7508Ae59C66c9", "Simple7702Account")
    ],
    56: [ # BNB
        # https://bscscan.com/address/0x4Cd241E8d1510e30b2076397afc7508Ae59C66c9
        ("4Cd241E8d1510e30b2076397afc7508Ae59C66c9", "Simple7702Account")
    ],
    137: [ # Polygon
        # https://polygonscan.com/address/0x4Cd241E8d1510e30b2076397afc7508Ae59C66c9
        ("4Cd241E8d1510e30b2076397afc7508Ae59C66c9", "Simple7702Account")
    ],
    100: [  # Gnosis
        # https://gnosisscan.io/address/0x5a7fc11397e9a8ad41bf10bf13f22b0a63f96f6d
        ("5a7fc11397e9a8ad41bf10bf13f22b0a63f96f6d", "Ambire"),
        # https://gnosisscan.io/address/0x63c0c19a282a1b52b07dd5a65b58948a07dae32b
        ("63c0c19a282a1b52b07dd5a65b58948a07dae32b", "MetaMask"),
    ],
    8453: [  # Base
        # https://basescan.org/address/0x5a7fc11397e9a8ad41bf10bf13f22b0a63f96f6d
        ("5a7fc11397e9a8ad41bf10bf13f22b0a63f96f6d", "Ambire"),
        # https://basescan.org/address/0x63c0c19a282a1b52b07dd5a65b58948a07dae32b
        ("63c0c19a282a1b52b07dd5a65b58948a07dae32b", "MetaMask"),
        # https://basescan.org/address/0x4Cd241E8d1510e30b2076397afc7508Ae59C66c9
        ("4Cd241E8d1510e30b2076397afc7508Ae59C66c9", "Simple7702Account")
    ],
    42161: [  # Arbitum
        # https://arbiscan.io/address/0x5a7fc11397e9a8ad41bf10bf13f22b0a63f96f6d
        ("5a7fc11397e9a8ad41bf10bf13f22b0a63f96f6d", "Ambire"),
        # https://arbiscan.io/address/0x63c0c19a282a1b52b07dd5a65b58948a07dae32b
        ("63c0c19a282a1b52b07dd5a65b58948a07dae32b", "MetaMask"),
        # https://arbiscan.io/address/0x4Cd241E8d1510e30b2076397afc7508Ae59C66c9
        ("4Cd241E8d1510e30b2076397afc7508Ae59C66c9", "Simple7702Account")
    ],
}
if 0 in _EIP7702_ADDRESSES:
    raise RuntimeError('"All chains" delegation is explicitly not supported')
%>
def lookup_eip7702_address(chain_id: int, address: bytes) -> str | None:
% for chain_id, items in _EIP7702_ADDRESSES.items():
    if chain_id == ${chain_id}:
% for addr, name in items:
        if address == ${fmt_addr(addr)}:
            return "${name}"
% endfor
        return None

% endfor
    return None
