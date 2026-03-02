from ubinascii import unhexlify

# https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/1inch/calldata-AggregationRouterV6.json#L9
ONEINCH_ADDRESS = unhexlify("111111125421cA6dc452d289314280a0f8842A65")
ONEINCH_CHAINS = [
    1,
    10,
    56,
    100,
    137,
    146,
    250,
    8217,
    8453,
    42161,
    43114,
    59144,
    1313161554,
]
ONEINCH_OWNER = "1inch Aggregation Router V6"

# https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/lifi/calldata-LIFIDiamond.json#L6
LIFI_ADDRESS = unhexlify("1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE")
LIFI_CHAINS = [
    1,
    10,
    25,
    56,
    100,
    106,
    122,
    137,
    204,
    250,
    252,
    288,
    324,
    1088,
    1284,
    1285,
    5000,
    8453,
    9001,
    34443,
    42161,
    42170,
    42220,
    43114,
    59144,
    81457,
    167004,
    534352,
    1313161554,
    1666600000,
]
LIFI_OWNER = "LiFI Diamond"

# https://etherscan.io/address/0xe592427a0aece92de3edee1f18e0157c05861564
UNISWAP_V3_ROUTER_ADDRESS = unhexlify("e592427a0aece92de3edee1f18e0157c05861564")
# https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/uniswap/calldata-UniswapV3Router02.json#L6
UNISWAP_V3_ROUTER_02_ADDRESS = unhexlify("68b3465833fb72A70ecDF485E0e4C7bD8665Fc45")
UNISWAP_V3_ROUTER_CHAINS = [1]
UNISWAP_OWNER = "Uniswap V3 Router"

KNOWN_ADDRESSES = {
    ONEINCH_ADDRESS: ONEINCH_OWNER,
    LIFI_ADDRESS: LIFI_OWNER,
    UNISWAP_V3_ROUTER_ADDRESS: UNISWAP_OWNER,
    UNISWAP_V3_ROUTER_02_ADDRESS: UNISWAP_OWNER,
}
