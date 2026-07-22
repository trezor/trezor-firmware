# TODO: To be removed once the protobuf definitions are updated with provider names.
def known_provider_name(chain_id: int, address: bytes) -> str | None:
    from ubinascii import unhexlify

    known_addresses = {
        # https://github.com/ethereum/clear-signing-erc7730-registry/blob/master/registry/1inch/calldata-AggregationRouterV6.json#L8
        (
            1,
            unhexlify("111111125421cA6dc452d289314280a0f8842A65"),
        ): "1inch Aggregation Router V6",
        # https://github.com/ethereum/clear-signing-erc7730-registry/blob/master/registry/lifi/calldata-LIFIDiamond.json
        (1, unhexlify("1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE")): "LI.FI Diamond",
        # https://github.com/ethereum/clear-signing-erc7730-registry/blob/master/registry/uniswap/calldata-UniswapV3Router02.json#L6
        (1, unhexlify("68b3465833fb72A70ecDF485E0e4C7bD8665Fc45")): "Uniswap V3 Router",
        # https://etherscan.io/address/0xe592427a0aece92de3edee1f18e0157c05861564
        (1, unhexlify("e592427a0aece92de3edee1f18e0157c05861564")): "Uniswap V3 Router",
        # Lido
        # https://etherscan.io/address/0x889edc2edab5f40e902b864ad4d7ade8e412f9b1
        (1, unhexlify("889edc2edab5f40e902b864ad4d7ade8e412f9b1")): "Lido",
        # https://etherscan.io/address/0xae7ab96520de3a18e5e111b5eaab095312d7fe84
        (1, unhexlify("ae7ab96520de3a18e5e111b5eaab095312d7fe84")): "Lido",
        # https://etherscan.io/address/0xa88f0329c2c4ce51ba3fc619bbf44efe7120dd0d
        (1, unhexlify("a88f0329c2c4ce51ba3fc619bbf44efe7120dd0d")): "Lido",
        # https://etherscan.io/address/0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0
        (1, unhexlify("7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0")): "Lido",
        # Morpho
        # https://etherscan.io/address/0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb
        (1, unhexlify("bbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb")): "Morpho",
        # https://basescan.org/address/0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb
        (8453, unhexlify("bbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb")): "Morpho",
        # https://etherscan.io/address/0x6566194141eefa99af43bb5aa71460ca2dc90245
        (1, unhexlify("6566194141eefa99af43bb5aa71460ca2dc90245")): "Morpho",
        # https://basescan.org/address/0x6bfd8137e702540e7a42b74178a4a49ba43920c4
        (8453, unhexlify("6bfd8137e702540e7a42b74178a4a49ba43920c4")): "Morpho",
        # Kiln
        # https://etherscan.io/address/0x576834cb068e677db4aff6ca245c7bde16c3867e
        (1, unhexlify("576834cb068e677db4aff6ca245c7bde16c3867e")): "Kiln",
        # https://etherscan.io/address/0x004c226fff73aa94b78a4df1a0e861797ba16819
        (1, unhexlify("004c226fff73aa94b78a4df1a0e861797ba16819")): "Kiln",
        # Missing account tag on ethscan. But contract deployer is tagged as Kiln.
        # Fresh high value transactions.
        # https://etherscan.io/address/0x8659eeff31cfcff580d37af8e7af250f8998aa83
        (1, unhexlify("8659eeff31cfcff580d37af8e7af250f8998aa83")): "Kiln",
        # Ethena
        # https://etherscan.io/address/0x9d39a5de30e57443bff2a8307a4256c8797a3497
        (1, unhexlify("9d39a5de30e57443bff2a8307a4256c8797a3497")): "Ethena",
        # StarkGate
        # https://etherscan.io/address/0xce5485cfb26914c5dce00b9baf0580364dafc7a4
        (1, unhexlify("ce5485cfb26914c5dce00b9baf0580364dafc7a4")): "StarkGate",
        # WalletConnect
        # https://optimistic.etherscan.io/address/0x521b4c065bbdbe3e20b3727340730936912dfa46
        (10, unhexlify("521b4c065bbdbe3e20b3727340730936912dfa46")): "WalletConnect",
        # https://optimistic.etherscan.io/address/0xef4461891dfb3ac8572ccf7c794664a8dd927945
        (10, unhexlify("ef4461891dfb3ac8572ccf7c794664a8dd927945")): "WalletConnect",
        # https://etherscan.io/address/0xef4461891dfb3ac8572ccf7c794664a8dd927945
        (1, unhexlify("ef4461891dfb3ac8572ccf7c794664a8dd927945")): "WalletConnect",
        # https://basescan.org/address/0xef4461891dfb3ac8572ccf7c794664a8dd927945
        (8453, unhexlify("ef4461891dfb3ac8572ccf7c794664a8dd927945")): "WalletConnect",
        # Core Stake
        # https://scan.coredao.org/address/0x0000000000000000000000000000000000001011
        (1116, unhexlify("0000000000000000000000000000000000001011")): "Core Stake",
        # https://scan.coredao.org/address/0x0000000000000000000000000000000000001010
        (1116, unhexlify("0000000000000000000000000000000000001010")): "Core Stake",
        # yield.xyz
        # https://etherscan.io/address/0xb929b89153fc2eed442e81e5a1add4e2fa39028f
        (1, unhexlify("b929b89153fc2eed442e81e5a1add4e2fa39028f")): "yield.xyz",
        # https://etherscan.io/address/0x56d783ca8e0b998c57a428bf1c26a8baca50524e
        (1, unhexlify("56d783ca8e0b998c57a428bf1c26a8baca50524e")): "yield.xyz",
        # https://etherscan.io/address/0x857679d69fe50e7b722f94acd2629d80c355163d
        (1, unhexlify("857679d69fe50e7b722f94acd2629d80c355163d")): "yield.xyz",
        # https://etherscan.io/address/0xf30cf4ed712d3734161fdaab5b1dbb49fd2d0e5c
        (1, unhexlify("f30cf4ed712d3734161fdaab5b1dbb49fd2d0e5c")): "yield.xyz",
        # https://etherscan.io/address/0x5a10de50160126a5f936506bd342c541ac44e943
        (1, unhexlify("5a10de50160126a5f936506bd342c541ac44e943")): "yield.xyz",
        # https://etherscan.io/address/0x35b1ca0f398905cf752e6fe122b51c88022fca32
        (1, unhexlify("35b1ca0f398905cf752e6fe122b51c88022fca32")): "yield.xyz",
        # https://etherscan.io/address/0xd9e6987d77bf2c6d0647b8181fd68a259f838c36
        (1, unhexlify("d9e6987d77bf2c6d0647b8181fd68a259f838c36")): "yield.xyz",
        # https://etherscan.io/address/0xd14a87025109013b0a2354a775cb335f926af65a
        (1, unhexlify("d14a87025109013b0a2354a775cb335f926af65a")): "yield.xyz",
        # https://etherscan.io/address/0xa6e768fef2d1af36c0cfdb276422e7881a83e951
        (1, unhexlify("a6e768fef2d1af36c0cfdb276422e7881a83e951")): "yield.xyz",
        # https://etherscan.io/address/0x467585aaea860f9d8b3b43bb994e4da8a93788a7
        (1, unhexlify("467585aaea860f9d8b3b43bb994e4da8a93788a7")): "yield.xyz",
        # https://etherscan.io/address/0x06998af8f39ff8630d1fb515d22781da4dc2ca71
        (1, unhexlify("06998af8f39ff8630d1fb515d22781da4dc2ca71")): "yield.xyz",
        # https://etherscan.io/address/0x875e901465a639f2e71fcfc10f426ed32f5a909a
        (1, unhexlify("875e901465a639f2e71fcfc10f426ed32f5a909a")): "yield.xyz",
        # https://etherscan.io/address/0x2905b3387c9550ea57fa3ee7d4b7e5abf3acd3d2
        (1, unhexlify("2905b3387c9550ea57fa3ee7d4b7e5abf3acd3d2")): "yield.xyz",
        # https://etherscan.io/address/0x15c2b3adca66e26b6f230b4023f52a285b7f9995
        (1, unhexlify("15c2b3adca66e26b6f230b4023f52a285b7f9995")): "yield.xyz",
    }
    return known_addresses.get((chain_id, address))
