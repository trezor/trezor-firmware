KNOWN_ADDRESSES = {
    # https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/1inch/calldata-AggregationRouterV6.json#L9
    (
        1,
        b"\x11\x11\x11\x12\x54\x21\xca\x6d\xc4\x52\xd2\x89\x31\x42\x80\xa0\xf8\x84\x2a\x65",
    ): "1inch Aggregation Router V6",
    # https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/lifi/calldata-LIFIDiamond.json
    (
        1,
        b"\x12\x31\xde\xb6\xf5\x74\x9e\xf6\xce\x69\x43\xa2\x75\xa1\xd3\xe7\x48\x6f\x4e\xae",
    ): "LiFI Diamond",
    # https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/registry/uniswap/calldata-UniswapV3Router02.json#L6
    (
        1,
        b"\x68\xb3\x46\x58\x33\xfb\x72\xa7\x0e\xcd\xf4\x85\xe0\xe4\xc7\xbd\x86\x65\xfc\x45",
    ): "Uniswap V3 Router",
    # https://etherscan.io/address/0xe592427a0aece92de3edee1f18e0157c05861564
    (
        1,
        b"\xe5\x92\x42\x7a\x0a\xec\xe9\x2d\xe3\xed\xee\x1f\x18\xe0\x15\x7c\x05\x86\x15\x64",
    ): "Uniswap V3 Router",
    # Lido
    # https://etherscan.io/address/0x889edc2edab5f40e902b864ad4d7ade8e412f9b1
    (
        1,
        b"\x88\x9e\xdc\x2e\xda\xb5\xf4\x0e\x90\x2b\x86\x4a\xd4\xd7\xad\xe8\xe4\x12\xf9\xb1",
    ): "Lido",
    # https://etherscan.io/address/0xae7ab96520de3a18e5e111b5eaab095312d7fe84
    (
        1,
        b"\xae\x7a\xb9\x65\x20\xde\x3a\x18\xe5\xe1\x11\xb5\xea\xab\x09\x53\x12\xd7\xfe\x84",
    ): "Lido",
    # https://etherscan.io/address/0xa88f0329c2c4ce51ba3fc619bbf44efe7120dd0d
    (
        1,
        b"\xa8\x8f\x03\x29\xc2\xc4\xce\x51\xba\x3f\xc6\x19\xbb\xf4\x4e\xfe\x71\x20\xdd\x0d",
    ): "Lido",
    # https://etherscan.io/address/0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0
    (
        1,
        b"\x7f\x39\xc5\x81\xf5\x95\xb5\x3c\x5c\xb1\x9b\xd0\xb3\xf8\xda\x6c\x93\x5e\x2c\xa0",
    ): "Lido",
    # Morpho
    # https://etherscan.io/address/0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb
    (
        1,
        b"\xbb\xbb\xbb\xbb\xbb\x9c\xc5\xe9\x0e\x3b\x3a\xf6\x4b\xda\xf6\x2c\x37\xee\xff\xcb",
    ): "Morpho",
    # https://basescan.org/address/0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb
    (
        8453,
        b"\xbb\xbb\xbb\xbb\xbb\x9c\xc5\xe9\x0e\x3b\x3a\xf6\x4b\xda\xf6\x2c\x37\xee\xff\xcb",
    ): "Morpho",
    # https://etherscan.io/address/0x6566194141eefa99af43bb5aa71460ca2dc90245
    (
        1,
        b"\x65\x66\x19\x41\x41\xee\xfa\x99\xaf\x43\xbb\x5a\xa7\x14\x60\xca\x2d\xc9\x02\x45",
    ): "Morpho",
    # https://basescan.org/address/0x6bfd8137e702540e7a42b74178a4a49ba43920c4
    (
        8453,
        b"\x6b\xfd\x81\x37\xe7\x02\x54\x0e\x7a\x42\xb7\x41\x78\xa4\xa4\x9b\xa4\x39\x20\xc4",
    ): "Morpho",
    # Kiln
    # https://etherscan.io/address/0x576834cb068e677db4aff6ca245c7bde16c3867e
    (
        1,
        b"\x57\x68\x34\xcb\x06\x8e\x67\x7d\xb4\xaf\xf6\xca\x24\x5c\x7b\xde\x16\xc3\x86\x7e",
    ): "Kiln",
    # https://etherscan.io/address/0x004c226fff73aa94b78a4df1a0e861797ba16819
    (
        1,
        b"\x00\x4c\x22\x6f\xff\x73\xaa\x94\xb7\x8a\x4d\xf1\xa0\xe8\x61\x79\x7b\xa1\x68\x19",
    ): "Kiln",
    # Missing account tag on ethscan. But contract deployer is tagged as Kiln.
    # Fresh high value transactions.
    # https://etherscan.io/address/0x8659eeff31cfcff580d37af8e7af250f8998aa83
    (
        1,
        b"\x86\x59\xee\xff\x31\xcf\xcf\xf5\x80\xd3\x7a\xf8\xe7\xaf\x25\x0f\x89\x98\xaa\x83",
    ): "Kiln",
    # Ethena
    # https://etherscan.io/address/0x9d39a5de30e57443bff2a8307a4256c8797a3497
    (
        1,
        b"\x9d\x39\xa5\xde\x30\xe5\x74\x43\xbf\xf2\xa8\x30\x7a\x42\x56\xc8\x79\x7a\x34\x97",
    ): "Ethena",
    # StarkGate
    # https://etherscan.io/address/0xce5485cfb26914c5dce00b9baf0580364dafc7a4
    (
        1,
        b"\xce\x54\x85\xcf\xb2\x69\x14\xc5\xdc\xe0\x0b\x9b\xaf\x05\x80\x36\x4d\xaf\xc7\xa4",
    ): "StarkGate",
    # WalletConnect
    # https://optimistic.etherscan.io/address/0x521b4c065bbdbe3e20b3727340730936912dfa46
    (
        10,
        b"\x52\x1b\x4c\x06\x5b\xbd\xbe\x3e\x20\xb3\x72\x73\x40\x73\x09\x36\x91\x2d\xfa\x46",
    ): "WalletConnect",
    # https://optimistic.etherscan.io/address/0xef4461891dfb3ac8572ccf7c794664a8dd927945
    (
        10,
        b"\xef\x44\x61\x89\x1d\xfb\x3a\xc8\x57\x2c\xcf\x7c\x79\x46\x64\xa8\xdd\x92\x79\x45",
    ): "WalletConnect",
    # https://etherscan.io/address/0xef4461891dfb3ac8572ccf7c794664a8dd927945
    (
        1,
        b"\xef\x44\x61\x89\x1d\xfb\x3a\xc8\x57\x2c\xcf\x7c\x79\x46\x64\xa8\xdd\x92\x79\x45",
    ): "WalletConnect",
    # https://basescan.org/address/0xef4461891dfb3ac8572ccf7c794664a8dd927945
    (
        8453,
        b"\xef\x44\x61\x89\x1d\xfb\x3a\xc8\x57\x2c\xcf\x7c\x79\x46\x64\xa8\xdd\x92\x79\x45",
    ): "WalletConnect",
    # Core Stake
    # https://scan.coredao.org/address/0x0000000000000000000000000000000000001011
    (
        1116,
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10\x11",
    ): "Core Stake",
    # https://scan.coredao.org/address/0x0000000000000000000000000000000000001010
    (
        1116,
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10\x10",
    ): "Core Stake",
    # yield.xyz
    # https://etherscan.io/address/0xb929b89153fc2eed442e81e5a1add4e2fa39028f
    (
        1,
        b"\xb9\x29\xb8\x91\x53\xfc\x2e\xed\x44\x2e\x81\xe5\xa1\xad\xd4\xe2\xfa\x39\x02\x8f",
    ): "yield.xyz",
    # https://etherscan.io/address/0x56d783ca8e0b998c57a428bf1c26a8baca50524e
    (
        1,
        b"\x56\xd7\x83\xca\x8e\x0b\x99\x8c\x57\xa4\x28\xbf\x1c\x26\xa8\xba\xca\x50\x52\x4e",
    ): "yield.xyz",
    # https://etherscan.io/address/0x857679d69fe50e7b722f94acd2629d80c355163d
    (
        1,
        b"\x85\x76\x79\xd6\x9f\xe5\x0e\x7b\x72\x2f\x94\xac\xd2\x62\x9d\x80\xc3\x55\x16\x3d",
    ): "yield.xyz",
    # https://etherscan.io/address/0xf30cf4ed712d3734161fdaab5b1dbb49fd2d0e5c
    (
        1,
        b"\xf3\x0c\xf4\xed\x71\x2d\x37\x34\x16\x1f\xda\xab\x5b\x1d\xbb\x49\xfd\x2d\x0e\x5c",
    ): "yield.xyz",
    # https://etherscan.io/address/0x5a10de50160126a5f936506bd342c541ac44e943
    (
        1,
        b"\x5a\x10\xde\x50\x16\x01\x26\xa5\xf9\x36\x50\x6b\xd3\x42\xc5\x41\xac\x44\xe9\x43",
    ): "yield.xyz",
    # https://etherscan.io/address/0x35b1ca0f398905cf752e6fe122b51c88022fca32
    (
        1,
        b"\x35\xb1\xca\x0f\x39\x89\x05\xcf\x75\x2e\x6f\xe1\x22\xb5\x1c\x88\x02\x2f\xca\x32",
    ): "yield.xyz",
    # https://etherscan.io/address/0xd9e6987d77bf2c6d0647b8181fd68a259f838c36
    (
        1,
        b"\xd9\xe6\x98\x7d\x77\xbf\x2c\x6d\x06\x47\xb8\x18\x1f\xd6\x8a\x25\x9f\x83\x8c\x36",
    ): "yield.xyz",
    # https://etherscan.io/address/0xd14a87025109013b0a2354a775cb335f926af65a
    (
        1,
        b"\xd1\x4a\x87\x02\x51\x09\x01\x3b\x0a\x23\x54\xa7\x75\xcb\x33\x5f\x92\x6a\xf6\x5a",
    ): "yield.xyz",
    # https://etherscan.io/address/0xa6e768fef2d1af36c0cfdb276422e7881a83e951
    (
        1,
        b"\xa6\xe7\x68\xfe\xf2\xd1\xaf\x36\xc0\xcf\xdb\x27\x64\x22\xe7\x88\x1a\x83\xe9\x51",
    ): "yield.xyz",
    # https://etherscan.io/address/0x467585aaea860f9d8b3b43bb994e4da8a93788a7
    (
        1,
        b"\x46\x75\x85\xaa\xea\x86\x0f\x9d\x8b\x3b\x43\xbb\x99\x4e\x4d\xa8\xa9\x37\x88\xa7",
    ): "yield.xyz",
    # https://etherscan.io/address/0x06998af8f39ff8630d1fb515d22781da4dc2ca71
    (
        1,
        b"\x06\x99\x8a\xf8\xf3\x9f\xf8\x63\x0d\x1f\xb5\x15\xd2\x27\x81\xda\x4d\xc2\xca\x71",
    ): "yield.xyz",
    # https://etherscan.io/address/0x875e901465a639f2e71fcfc10f426ed32f5a909a
    (
        1,
        b"\x87\x5e\x90\x14\x65\xa6\x39\xf2\xe7\x1f\xcf\xc1\x0f\x42\x6e\xd3\x2f\x5a\x90\x9a",
    ): "yield.xyz",
    # https://etherscan.io/address/0x2905b3387c9550ea57fa3ee7d4b7e5abf3acd3d2
    (
        1,
        b"\x29\x05\xb3\x38\x7c\x95\x50\xea\x57\xfa\x3e\xe7\xd4\xb7\xe5\xab\xf3\xac\xd3\xd2",
    ): "yield.xyz",
    # https://etherscan.io/address/0x15c2b3adca66e26b6f230b4023f52a285b7f9995
    (
        1,
        b"\x15\xc2\xb3\xad\xca\x66\xe2\x6b\x6f\x23\x0b\x40\x23\xf5\x2a\x28\x5b\x7f\x99\x95",
    ): "yield.xyz",
}

if __debug__:
    KNOWN_ADDRESSES[
        (
            1,
            b"\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd\xdd",
        )
    ] = "Trezor Test. DO NOT USE"
