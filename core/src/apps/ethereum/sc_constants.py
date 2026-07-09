from ubinascii import unhexlify

KNOWN_ADDRESSES = {
    # https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/1inch/calldata-AggregationRouterV6.json#L9
    unhexlify(
        "111111125421cA6dc452d289314280a0f8842A65"
    ): "1inch Aggregation Router V6",
    # https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/lifi/calldata-LIFIDiamond.json
    unhexlify("1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE"): "LiFI Diamond",
    # https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/uniswap/calldata-UniswapV3Router02.json#L6
    unhexlify("68b3465833fb72A70ecDF485E0e4C7bD8665Fc45"): "Uniswap V3 Router",
    # https://etherscan.io/address/0xe592427a0aece92de3edee1f18e0157c05861564
    unhexlify("e592427a0aece92de3edee1f18e0157c05861564"): "Uniswap V3 Router",
}
