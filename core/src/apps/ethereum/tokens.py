# generated from tokens.py.mako
# (by running `make templates` in `core`)
# do not edit manually!
# fmt: off

# NOTE: returning a tuple instead of `TokenInfo` from the "data" function
# saves 5600 bytes of flash size. Implementing the `_token_iterator`
# instead of if-tree approach saves another 5600 bytes.

# NOTE: interestingly, it did not save much flash size to use smaller
# parts of the address, for example address length of 10 bytes saves
# 1 byte per entry, so 1887 bytes overall (and further decrease does not help).
# (The idea was not having to store the whole address, even a smaller part
# of it has enough collision-resistance.)
# (In the if-tree approach the address length did not have any effect whatsoever.)

from typing import Iterator

from trezor import utils
from trezor.messages import EthereumTokenInfo

UNKNOWN_TOKEN = EthereumTokenInfo(
    symbol="Wei UNKN",
    decimals=0,
    address=b"",
    chain_id=0,
    name="Unknown token",
)


def token_by_chain_address(chain_id: int, address: bytes) -> EthereumTokenInfo | None:
    for addr, symbol, decimal, name in _token_iterator(chain_id):
        if address == addr:
            return EthereumTokenInfo(
                symbol=symbol,
                decimals=decimal,
                address=address,
                chain_id=chain_id,
                name=name,
            )
    return None


def _token_iterator(chain_id: int) -> Iterator[tuple[bytes, str, int, str]]:
    if utils.INTERNAL_MODEL == "T2B1":
        if chain_id == 1:  # eth
            yield (  # address, symbol, decimals, name
                b"\x7f\xc6\x65\x00\xc8\x4a\x76\xad\x7e\x9c\x93\x43\x7b\xfc\x5a\xc3\x3e\x2d\xda\xe9",
                "AAVE",
                18,
                "Aave",
            )
            yield (  # address, symbol, decimals, name
                b"\x4d\x22\x44\x52\x80\x1a\xce\xd8\xb2\xf0\xae\xbe\x15\x53\x79\xbb\x5d\x59\x43\x81",
                "APE",
                18,
                "ApeCoin",
            )
            yield (  # address, symbol, decimals, name
                b"\xbb\x0e\x17\xef\x65\xf8\x2a\xb0\x18\xd8\xed\xd7\x76\xe8\xdd\x94\x03\x27\xb2\x8b",
                "AXS",
                18,
                "Axie Infinity",
            )
            yield (  # address, symbol, decimals, name
                b"\x4f\xab\xb1\x45\xd6\x46\x52\xa9\x48\xd7\x25\x33\x02\x3f\x6e\x7a\x62\x3c\x7c\x53",
                "BUSD",
                18,
                "Binance USD",
            )
            yield (  # address, symbol, decimals, name
                b"\x35\x06\x42\x4f\x91\xfd\x33\x08\x44\x66\xf4\x02\xd5\xd9\x7f\x05\xf8\xe3\xb4\xaf",
                "CHZ",
                18,
                "Chiliz",
            )
            yield (  # address, symbol, decimals, name
                b"\xa0\xb7\x3e\x1f\xf0\xb8\x09\x14\xab\x6f\xe0\x44\x4e\x65\x84\x8c\x4c\x34\x45\x0b",
                "CRO",
                8,
                "Cronos",
            )
            yield (  # address, symbol, decimals, name
                b"\x6b\x17\x54\x74\xe8\x90\x94\xc4\x4d\xa9\x8b\x95\x4e\xed\xea\xc4\x95\x27\x1d\x0f",
                "DAI",
                18,
                "Dai",
            )
            yield (  # address, symbol, decimals, name
                b"\x85\x3d\x95\x5a\xce\xf8\x22\xdb\x05\x8e\xb8\x50\x59\x11\xed\x77\xf1\x75\xb9\x9e",
                "FRAX",
                18,
                "Frax",
            )
            yield (  # address, symbol, decimals, name
                b"\x2a\xf5\xd2\xad\x76\x74\x11\x91\xd1\x5d\xfe\x7b\xf6\xac\x92\xd4\xbd\x91\x2c\xa3",
                "LEO",
                18,
                "LEO Token",
            )
            yield (  # address, symbol, decimals, name
                b"\x51\x49\x10\x77\x1a\xf9\xca\x65\x6a\xf8\x40\xdf\xf8\x3e\x82\x64\xec\xf9\x86\xca",
                "LINK",
                18,
                "Chainlink",
            )
            yield (  # address, symbol, decimals, name
                b"\x0f\x5d\x2f\xb2\x9f\xb7\xd3\xcf\xee\x44\x4a\x20\x02\x98\xf4\x68\x90\x8c\xc9\x42",
                "MANA",
                18,
                "Decentraland",
            )
            yield (  # address, symbol, decimals, name
                b"\x7d\x1a\xfa\x7b\x71\x8f\xb8\x93\xdb\x30\xa3\xab\xc0\xcf\xc6\x08\xaa\xcf\xeb\xb0",
                "MATIC",
                18,
                "Polygon",
            )
            yield (  # address, symbol, decimals, name
                b"\x75\x23\x1f\x58\xb4\x32\x40\xc9\x71\x8d\xd5\x8b\x49\x67\xc5\x11\x43\x42\xa8\x6c",
                "OKB",
                18,
                "OKB",
            )
            yield (  # address, symbol, decimals, name
                b"\x4a\x22\x0e\x60\x96\xb2\x5e\xad\xb8\x83\x58\xcb\x44\x06\x8a\x32\x48\x25\x46\x75",
                "QNT",
                18,
                "Quant",
            )
            yield (  # address, symbol, decimals, name
                b"\x38\x45\xba\xda\xde\x8e\x6d\xff\x04\x98\x20\x68\x0d\x1f\x14\xbd\x39\x03\xa5\xd0",
                "SAND",
                18,
                "The Sandbox",
            )
            yield (  # address, symbol, decimals, name
                b"\x95\xad\x61\xb0\xa1\x50\xd7\x92\x19\xdc\xf6\x4e\x1e\x6c\xc0\x1f\x0b\x64\xc4\xce",
                "SHIB",
                18,
                "Shiba Inu",
            )
            yield (  # address, symbol, decimals, name
                b"\xae\x7a\xb9\x65\x20\xde\x3a\x18\xe5\xe1\x11\xb5\xea\xab\x09\x53\x12\xd7\xfe\x84",
                "STETH",
                18,
                "Lido Staked Ether",
            )
            yield (  # address, symbol, decimals, name
                b"\x1f\x98\x40\xa8\x5d\x5a\xf5\xbf\x1d\x17\x62\xf9\x25\xbd\xad\xdc\x42\x01\xf9\x84",
                "UNI",
                18,
                "Uniswap",
            )
            yield (  # address, symbol, decimals, name
                b"\xa0\xb8\x69\x91\xc6\x21\x8b\x36\xc1\xd1\x9d\x4a\x2e\x9e\xb0\xce\x36\x06\xeb\x48",
                "USDC",
                6,
                "USD Coin",
            )
            yield (  # address, symbol, decimals, name
                b"\xda\xc1\x7f\x95\x8d\x2e\xe5\x23\xa2\x20\x62\x06\x99\x45\x97\xc1\x3d\x83\x1e\xc7",
                "USDT",
                6,
                "Tether",
            )
            yield (  # address, symbol, decimals, name
                b"\x22\x60\xfa\xc5\xe5\x54\x2a\x77\x3a\xa4\x4f\xbc\xfe\xdf\x7c\x19\x3b\xc2\xc5\x99",
                "WBTC",
                8,
                "Wrapped Bitcoin",
            )
            yield (  # address, symbol, decimals, name
                b"\xa2\xcd\x3d\x43\xc7\x75\x97\x8a\x96\xbd\xbf\x12\xd7\x33\xd5\xa1\xed\x94\xfb\x18",
                "XCN",
                18,
                "Chain",
            )
        if chain_id == 56:  # bnb
            yield (  # address, symbol, decimals, name
                b"\x0e\xb3\xa7\x05\xfc\x54\x72\x50\x37\xcc\x9e\x00\x8b\xde\xde\x69\x7f\x62\xf3\x35",
                "ATOM",
                18,
                "Cosmos Hub",
            )
        if chain_id == 137:  # matic
            yield (  # address, symbol, decimals, name
                b"\x2c\x89\xbb\xc9\x2b\xd8\x6f\x80\x75\xd1\xde\xcc\x58\xc7\xf4\xe0\x10\x7f\x28\x6b",
                "WAVAX",
                18,
                "Wrapped AVAX",
            )
    if utils.INTERNAL_MODEL == "T2T1":
        if chain_id == 1:  # eth
            yield (  # address, symbol, decimals, name
                b"\x7f\xc6\x65\x00\xc8\x4a\x76\xad\x7e\x9c\x93\x43\x7b\xfc\x5a\xc3\x3e\x2d\xda\xe9",
                "AAVE",
                18,
                "Aave",
            )
            yield (  # address, symbol, decimals, name
                b"\x4d\x22\x44\x52\x80\x1a\xce\xd8\xb2\xf0\xae\xbe\x15\x53\x79\xbb\x5d\x59\x43\x81",
                "APE",
                18,
                "ApeCoin",
            )
            yield (  # address, symbol, decimals, name
                b"\xbb\x0e\x17\xef\x65\xf8\x2a\xb0\x18\xd8\xed\xd7\x76\xe8\xdd\x94\x03\x27\xb2\x8b",
                "AXS",
                18,
                "Axie Infinity",
            )
            yield (  # address, symbol, decimals, name
                b"\x4f\xab\xb1\x45\xd6\x46\x52\xa9\x48\xd7\x25\x33\x02\x3f\x6e\x7a\x62\x3c\x7c\x53",
                "BUSD",
                18,
                "Binance USD",
            )
            yield (  # address, symbol, decimals, name
                b"\x35\x06\x42\x4f\x91\xfd\x33\x08\x44\x66\xf4\x02\xd5\xd9\x7f\x05\xf8\xe3\xb4\xaf",
                "CHZ",
                18,
                "Chiliz",
            )
            yield (  # address, symbol, decimals, name
                b"\xa0\xb7\x3e\x1f\xf0\xb8\x09\x14\xab\x6f\xe0\x44\x4e\x65\x84\x8c\x4c\x34\x45\x0b",
                "CRO",
                8,
                "Cronos",
            )
            yield (  # address, symbol, decimals, name
                b"\x6b\x17\x54\x74\xe8\x90\x94\xc4\x4d\xa9\x8b\x95\x4e\xed\xea\xc4\x95\x27\x1d\x0f",
                "DAI",
                18,
                "Dai",
            )
            yield (  # address, symbol, decimals, name
                b"\x85\x3d\x95\x5a\xce\xf8\x22\xdb\x05\x8e\xb8\x50\x59\x11\xed\x77\xf1\x75\xb9\x9e",
                "FRAX",
                18,
                "Frax",
            )
            yield (  # address, symbol, decimals, name
                b"\x2a\xf5\xd2\xad\x76\x74\x11\x91\xd1\x5d\xfe\x7b\xf6\xac\x92\xd4\xbd\x91\x2c\xa3",
                "LEO",
                18,
                "LEO Token",
            )
            yield (  # address, symbol, decimals, name
                b"\x51\x49\x10\x77\x1a\xf9\xca\x65\x6a\xf8\x40\xdf\xf8\x3e\x82\x64\xec\xf9\x86\xca",
                "LINK",
                18,
                "Chainlink",
            )
            yield (  # address, symbol, decimals, name
                b"\x0f\x5d\x2f\xb2\x9f\xb7\xd3\xcf\xee\x44\x4a\x20\x02\x98\xf4\x68\x90\x8c\xc9\x42",
                "MANA",
                18,
                "Decentraland",
            )
            yield (  # address, symbol, decimals, name
                b"\x7d\x1a\xfa\x7b\x71\x8f\xb8\x93\xdb\x30\xa3\xab\xc0\xcf\xc6\x08\xaa\xcf\xeb\xb0",
                "MATIC",
                18,
                "Polygon",
            )
            yield (  # address, symbol, decimals, name
                b"\x75\x23\x1f\x58\xb4\x32\x40\xc9\x71\x8d\xd5\x8b\x49\x67\xc5\x11\x43\x42\xa8\x6c",
                "OKB",
                18,
                "OKB",
            )
            yield (  # address, symbol, decimals, name
                b"\x4a\x22\x0e\x60\x96\xb2\x5e\xad\xb8\x83\x58\xcb\x44\x06\x8a\x32\x48\x25\x46\x75",
                "QNT",
                18,
                "Quant",
            )
            yield (  # address, symbol, decimals, name
                b"\x38\x45\xba\xda\xde\x8e\x6d\xff\x04\x98\x20\x68\x0d\x1f\x14\xbd\x39\x03\xa5\xd0",
                "SAND",
                18,
                "The Sandbox",
            )
            yield (  # address, symbol, decimals, name
                b"\x95\xad\x61\xb0\xa1\x50\xd7\x92\x19\xdc\xf6\x4e\x1e\x6c\xc0\x1f\x0b\x64\xc4\xce",
                "SHIB",
                18,
                "Shiba Inu",
            )
            yield (  # address, symbol, decimals, name
                b"\xae\x7a\xb9\x65\x20\xde\x3a\x18\xe5\xe1\x11\xb5\xea\xab\x09\x53\x12\xd7\xfe\x84",
                "STETH",
                18,
                "Lido Staked Ether",
            )
            yield (  # address, symbol, decimals, name
                b"\x1f\x98\x40\xa8\x5d\x5a\xf5\xbf\x1d\x17\x62\xf9\x25\xbd\xad\xdc\x42\x01\xf9\x84",
                "UNI",
                18,
                "Uniswap",
            )
            yield (  # address, symbol, decimals, name
                b"\xa0\xb8\x69\x91\xc6\x21\x8b\x36\xc1\xd1\x9d\x4a\x2e\x9e\xb0\xce\x36\x06\xeb\x48",
                "USDC",
                6,
                "USD Coin",
            )
            yield (  # address, symbol, decimals, name
                b"\xda\xc1\x7f\x95\x8d\x2e\xe5\x23\xa2\x20\x62\x06\x99\x45\x97\xc1\x3d\x83\x1e\xc7",
                "USDT",
                6,
                "Tether",
            )
            yield (  # address, symbol, decimals, name
                b"\x22\x60\xfa\xc5\xe5\x54\x2a\x77\x3a\xa4\x4f\xbc\xfe\xdf\x7c\x19\x3b\xc2\xc5\x99",
                "WBTC",
                8,
                "Wrapped Bitcoin",
            )
            yield (  # address, symbol, decimals, name
                b"\xa2\xcd\x3d\x43\xc7\x75\x97\x8a\x96\xbd\xbf\x12\xd7\x33\xd5\xa1\xed\x94\xfb\x18",
                "XCN",
                18,
                "Chain",
            )
        if chain_id == 56:  # bnb
            yield (  # address, symbol, decimals, name
                b"\x0e\xb3\xa7\x05\xfc\x54\x72\x50\x37\xcc\x9e\x00\x8b\xde\xde\x69\x7f\x62\xf3\x35",
                "ATOM",
                18,
                "Cosmos Hub",
            )
        if chain_id == 137:  # matic
            yield (  # address, symbol, decimals, name
                b"\x2c\x89\xbb\xc9\x2b\xd8\x6f\x80\x75\xd1\xde\xcc\x58\xc7\xf4\xe0\x10\x7f\x28\x6b",
                "WAVAX",
                18,
                "Wrapped AVAX",
            )
    if utils.INTERNAL_MODEL == "T3B1":
        if chain_id == 1:  # eth
            yield (  # address, symbol, decimals, name
                b"\x7f\xc6\x65\x00\xc8\x4a\x76\xad\x7e\x9c\x93\x43\x7b\xfc\x5a\xc3\x3e\x2d\xda\xe9",
                "AAVE",
                18,
                "Aave",
            )
            yield (  # address, symbol, decimals, name
                b"\x4d\x22\x44\x52\x80\x1a\xce\xd8\xb2\xf0\xae\xbe\x15\x53\x79\xbb\x5d\x59\x43\x81",
                "APE",
                18,
                "ApeCoin",
            )
            yield (  # address, symbol, decimals, name
                b"\xbb\x0e\x17\xef\x65\xf8\x2a\xb0\x18\xd8\xed\xd7\x76\xe8\xdd\x94\x03\x27\xb2\x8b",
                "AXS",
                18,
                "Axie Infinity",
            )
            yield (  # address, symbol, decimals, name
                b"\x4f\xab\xb1\x45\xd6\x46\x52\xa9\x48\xd7\x25\x33\x02\x3f\x6e\x7a\x62\x3c\x7c\x53",
                "BUSD",
                18,
                "Binance USD",
            )
            yield (  # address, symbol, decimals, name
                b"\x35\x06\x42\x4f\x91\xfd\x33\x08\x44\x66\xf4\x02\xd5\xd9\x7f\x05\xf8\xe3\xb4\xaf",
                "CHZ",
                18,
                "Chiliz",
            )
            yield (  # address, symbol, decimals, name
                b"\xa0\xb7\x3e\x1f\xf0\xb8\x09\x14\xab\x6f\xe0\x44\x4e\x65\x84\x8c\x4c\x34\x45\x0b",
                "CRO",
                8,
                "Cronos",
            )
            yield (  # address, symbol, decimals, name
                b"\x6b\x17\x54\x74\xe8\x90\x94\xc4\x4d\xa9\x8b\x95\x4e\xed\xea\xc4\x95\x27\x1d\x0f",
                "DAI",
                18,
                "Dai",
            )
            yield (  # address, symbol, decimals, name
                b"\x85\x3d\x95\x5a\xce\xf8\x22\xdb\x05\x8e\xb8\x50\x59\x11\xed\x77\xf1\x75\xb9\x9e",
                "FRAX",
                18,
                "Frax",
            )
            yield (  # address, symbol, decimals, name
                b"\x2a\xf5\xd2\xad\x76\x74\x11\x91\xd1\x5d\xfe\x7b\xf6\xac\x92\xd4\xbd\x91\x2c\xa3",
                "LEO",
                18,
                "LEO Token",
            )
            yield (  # address, symbol, decimals, name
                b"\x51\x49\x10\x77\x1a\xf9\xca\x65\x6a\xf8\x40\xdf\xf8\x3e\x82\x64\xec\xf9\x86\xca",
                "LINK",
                18,
                "Chainlink",
            )
            yield (  # address, symbol, decimals, name
                b"\x0f\x5d\x2f\xb2\x9f\xb7\xd3\xcf\xee\x44\x4a\x20\x02\x98\xf4\x68\x90\x8c\xc9\x42",
                "MANA",
                18,
                "Decentraland",
            )
            yield (  # address, symbol, decimals, name
                b"\x7d\x1a\xfa\x7b\x71\x8f\xb8\x93\xdb\x30\xa3\xab\xc0\xcf\xc6\x08\xaa\xcf\xeb\xb0",
                "MATIC",
                18,
                "Polygon",
            )
            yield (  # address, symbol, decimals, name
                b"\x75\x23\x1f\x58\xb4\x32\x40\xc9\x71\x8d\xd5\x8b\x49\x67\xc5\x11\x43\x42\xa8\x6c",
                "OKB",
                18,
                "OKB",
            )
            yield (  # address, symbol, decimals, name
                b"\x4a\x22\x0e\x60\x96\xb2\x5e\xad\xb8\x83\x58\xcb\x44\x06\x8a\x32\x48\x25\x46\x75",
                "QNT",
                18,
                "Quant",
            )
            yield (  # address, symbol, decimals, name
                b"\x38\x45\xba\xda\xde\x8e\x6d\xff\x04\x98\x20\x68\x0d\x1f\x14\xbd\x39\x03\xa5\xd0",
                "SAND",
                18,
                "The Sandbox",
            )
            yield (  # address, symbol, decimals, name
                b"\x95\xad\x61\xb0\xa1\x50\xd7\x92\x19\xdc\xf6\x4e\x1e\x6c\xc0\x1f\x0b\x64\xc4\xce",
                "SHIB",
                18,
                "Shiba Inu",
            )
            yield (  # address, symbol, decimals, name
                b"\xae\x7a\xb9\x65\x20\xde\x3a\x18\xe5\xe1\x11\xb5\xea\xab\x09\x53\x12\xd7\xfe\x84",
                "STETH",
                18,
                "Lido Staked Ether",
            )
            yield (  # address, symbol, decimals, name
                b"\x1f\x98\x40\xa8\x5d\x5a\xf5\xbf\x1d\x17\x62\xf9\x25\xbd\xad\xdc\x42\x01\xf9\x84",
                "UNI",
                18,
                "Uniswap",
            )
            yield (  # address, symbol, decimals, name
                b"\xa0\xb8\x69\x91\xc6\x21\x8b\x36\xc1\xd1\x9d\x4a\x2e\x9e\xb0\xce\x36\x06\xeb\x48",
                "USDC",
                6,
                "USD Coin",
            )
            yield (  # address, symbol, decimals, name
                b"\xda\xc1\x7f\x95\x8d\x2e\xe5\x23\xa2\x20\x62\x06\x99\x45\x97\xc1\x3d\x83\x1e\xc7",
                "USDT",
                6,
                "Tether",
            )
            yield (  # address, symbol, decimals, name
                b"\x22\x60\xfa\xc5\xe5\x54\x2a\x77\x3a\xa4\x4f\xbc\xfe\xdf\x7c\x19\x3b\xc2\xc5\x99",
                "WBTC",
                8,
                "Wrapped Bitcoin",
            )
            yield (  # address, symbol, decimals, name
                b"\xa2\xcd\x3d\x43\xc7\x75\x97\x8a\x96\xbd\xbf\x12\xd7\x33\xd5\xa1\xed\x94\xfb\x18",
                "XCN",
                18,
                "Chain",
            )
        if chain_id == 56:  # bnb
            yield (  # address, symbol, decimals, name
                b"\x0e\xb3\xa7\x05\xfc\x54\x72\x50\x37\xcc\x9e\x00\x8b\xde\xde\x69\x7f\x62\xf3\x35",
                "ATOM",
                18,
                "Cosmos Hub",
            )
        if chain_id == 137:  # matic
            yield (  # address, symbol, decimals, name
                b"\x2c\x89\xbb\xc9\x2b\xd8\x6f\x80\x75\xd1\xde\xcc\x58\xc7\xf4\xe0\x10\x7f\x28\x6b",
                "WAVAX",
                18,
                "Wrapped AVAX",
            )
    if utils.INTERNAL_MODEL == "T3T1":
        if chain_id == 1:  # eth
            yield (  # address, symbol, decimals, name
                b"\x7f\xc6\x65\x00\xc8\x4a\x76\xad\x7e\x9c\x93\x43\x7b\xfc\x5a\xc3\x3e\x2d\xda\xe9",
                "AAVE",
                18,
                "Aave",
            )
            yield (  # address, symbol, decimals, name
                b"\x4d\x22\x44\x52\x80\x1a\xce\xd8\xb2\xf0\xae\xbe\x15\x53\x79\xbb\x5d\x59\x43\x81",
                "APE",
                18,
                "ApeCoin",
            )
            yield (  # address, symbol, decimals, name
                b"\xbb\x0e\x17\xef\x65\xf8\x2a\xb0\x18\xd8\xed\xd7\x76\xe8\xdd\x94\x03\x27\xb2\x8b",
                "AXS",
                18,
                "Axie Infinity",
            )
            yield (  # address, symbol, decimals, name
                b"\x4f\xab\xb1\x45\xd6\x46\x52\xa9\x48\xd7\x25\x33\x02\x3f\x6e\x7a\x62\x3c\x7c\x53",
                "BUSD",
                18,
                "Binance USD",
            )
            yield (  # address, symbol, decimals, name
                b"\x35\x06\x42\x4f\x91\xfd\x33\x08\x44\x66\xf4\x02\xd5\xd9\x7f\x05\xf8\xe3\xb4\xaf",
                "CHZ",
                18,
                "Chiliz",
            )
            yield (  # address, symbol, decimals, name
                b"\xa0\xb7\x3e\x1f\xf0\xb8\x09\x14\xab\x6f\xe0\x44\x4e\x65\x84\x8c\x4c\x34\x45\x0b",
                "CRO",
                8,
                "Cronos",
            )
            yield (  # address, symbol, decimals, name
                b"\x6b\x17\x54\x74\xe8\x90\x94\xc4\x4d\xa9\x8b\x95\x4e\xed\xea\xc4\x95\x27\x1d\x0f",
                "DAI",
                18,
                "Dai",
            )
            yield (  # address, symbol, decimals, name
                b"\x85\x3d\x95\x5a\xce\xf8\x22\xdb\x05\x8e\xb8\x50\x59\x11\xed\x77\xf1\x75\xb9\x9e",
                "FRAX",
                18,
                "Frax",
            )
            yield (  # address, symbol, decimals, name
                b"\x2a\xf5\xd2\xad\x76\x74\x11\x91\xd1\x5d\xfe\x7b\xf6\xac\x92\xd4\xbd\x91\x2c\xa3",
                "LEO",
                18,
                "LEO Token",
            )
            yield (  # address, symbol, decimals, name
                b"\x51\x49\x10\x77\x1a\xf9\xca\x65\x6a\xf8\x40\xdf\xf8\x3e\x82\x64\xec\xf9\x86\xca",
                "LINK",
                18,
                "Chainlink",
            )
            yield (  # address, symbol, decimals, name
                b"\x0f\x5d\x2f\xb2\x9f\xb7\xd3\xcf\xee\x44\x4a\x20\x02\x98\xf4\x68\x90\x8c\xc9\x42",
                "MANA",
                18,
                "Decentraland",
            )
            yield (  # address, symbol, decimals, name
                b"\x7d\x1a\xfa\x7b\x71\x8f\xb8\x93\xdb\x30\xa3\xab\xc0\xcf\xc6\x08\xaa\xcf\xeb\xb0",
                "MATIC",
                18,
                "Polygon",
            )
            yield (  # address, symbol, decimals, name
                b"\x75\x23\x1f\x58\xb4\x32\x40\xc9\x71\x8d\xd5\x8b\x49\x67\xc5\x11\x43\x42\xa8\x6c",
                "OKB",
                18,
                "OKB",
            )
            yield (  # address, symbol, decimals, name
                b"\x4a\x22\x0e\x60\x96\xb2\x5e\xad\xb8\x83\x58\xcb\x44\x06\x8a\x32\x48\x25\x46\x75",
                "QNT",
                18,
                "Quant",
            )
            yield (  # address, symbol, decimals, name
                b"\x38\x45\xba\xda\xde\x8e\x6d\xff\x04\x98\x20\x68\x0d\x1f\x14\xbd\x39\x03\xa5\xd0",
                "SAND",
                18,
                "The Sandbox",
            )
            yield (  # address, symbol, decimals, name
                b"\x95\xad\x61\xb0\xa1\x50\xd7\x92\x19\xdc\xf6\x4e\x1e\x6c\xc0\x1f\x0b\x64\xc4\xce",
                "SHIB",
                18,
                "Shiba Inu",
            )
            yield (  # address, symbol, decimals, name
                b"\xae\x7a\xb9\x65\x20\xde\x3a\x18\xe5\xe1\x11\xb5\xea\xab\x09\x53\x12\xd7\xfe\x84",
                "STETH",
                18,
                "Lido Staked Ether",
            )
            yield (  # address, symbol, decimals, name
                b"\x1f\x98\x40\xa8\x5d\x5a\xf5\xbf\x1d\x17\x62\xf9\x25\xbd\xad\xdc\x42\x01\xf9\x84",
                "UNI",
                18,
                "Uniswap",
            )
            yield (  # address, symbol, decimals, name
                b"\xa0\xb8\x69\x91\xc6\x21\x8b\x36\xc1\xd1\x9d\x4a\x2e\x9e\xb0\xce\x36\x06\xeb\x48",
                "USDC",
                6,
                "USD Coin",
            )
            yield (  # address, symbol, decimals, name
                b"\xda\xc1\x7f\x95\x8d\x2e\xe5\x23\xa2\x20\x62\x06\x99\x45\x97\xc1\x3d\x83\x1e\xc7",
                "USDT",
                6,
                "Tether",
            )
            yield (  # address, symbol, decimals, name
                b"\x22\x60\xfa\xc5\xe5\x54\x2a\x77\x3a\xa4\x4f\xbc\xfe\xdf\x7c\x19\x3b\xc2\xc5\x99",
                "WBTC",
                8,
                "Wrapped Bitcoin",
            )
            yield (  # address, symbol, decimals, name
                b"\xa2\xcd\x3d\x43\xc7\x75\x97\x8a\x96\xbd\xbf\x12\xd7\x33\xd5\xa1\xed\x94\xfb\x18",
                "XCN",
                18,
                "Chain",
            )
        if chain_id == 56:  # bnb
            yield (  # address, symbol, decimals, name
                b"\x0e\xb3\xa7\x05\xfc\x54\x72\x50\x37\xcc\x9e\x00\x8b\xde\xde\x69\x7f\x62\xf3\x35",
                "ATOM",
                18,
                "Cosmos Hub",
            )
        if chain_id == 137:  # matic
            yield (  # address, symbol, decimals, name
                b"\x2c\x89\xbb\xc9\x2b\xd8\x6f\x80\x75\xd1\xde\xcc\x58\xc7\xf4\xe0\x10\x7f\x28\x6b",
                "WAVAX",
                18,
                "Wrapped AVAX",
            )
    if utils.INTERNAL_MODEL == "T3W1":
        if chain_id == 1:  # eth
            yield (  # address, symbol, decimals, name
                b"\x7f\xc6\x65\x00\xc8\x4a\x76\xad\x7e\x9c\x93\x43\x7b\xfc\x5a\xc3\x3e\x2d\xda\xe9",
                "AAVE",
                18,
                "Aave",
            )
            yield (  # address, symbol, decimals, name
                b"\x4d\x22\x44\x52\x80\x1a\xce\xd8\xb2\xf0\xae\xbe\x15\x53\x79\xbb\x5d\x59\x43\x81",
                "APE",
                18,
                "ApeCoin",
            )
            yield (  # address, symbol, decimals, name
                b"\xbb\x0e\x17\xef\x65\xf8\x2a\xb0\x18\xd8\xed\xd7\x76\xe8\xdd\x94\x03\x27\xb2\x8b",
                "AXS",
                18,
                "Axie Infinity",
            )
            yield (  # address, symbol, decimals, name
                b"\x4f\xab\xb1\x45\xd6\x46\x52\xa9\x48\xd7\x25\x33\x02\x3f\x6e\x7a\x62\x3c\x7c\x53",
                "BUSD",
                18,
                "Binance USD",
            )
            yield (  # address, symbol, decimals, name
                b"\x35\x06\x42\x4f\x91\xfd\x33\x08\x44\x66\xf4\x02\xd5\xd9\x7f\x05\xf8\xe3\xb4\xaf",
                "CHZ",
                18,
                "Chiliz",
            )
            yield (  # address, symbol, decimals, name
                b"\xa0\xb7\x3e\x1f\xf0\xb8\x09\x14\xab\x6f\xe0\x44\x4e\x65\x84\x8c\x4c\x34\x45\x0b",
                "CRO",
                8,
                "Cronos",
            )
            yield (  # address, symbol, decimals, name
                b"\x6b\x17\x54\x74\xe8\x90\x94\xc4\x4d\xa9\x8b\x95\x4e\xed\xea\xc4\x95\x27\x1d\x0f",
                "DAI",
                18,
                "Dai",
            )
            yield (  # address, symbol, decimals, name
                b"\x85\x3d\x95\x5a\xce\xf8\x22\xdb\x05\x8e\xb8\x50\x59\x11\xed\x77\xf1\x75\xb9\x9e",
                "FRAX",
                18,
                "Frax",
            )
            yield (  # address, symbol, decimals, name
                b"\x2a\xf5\xd2\xad\x76\x74\x11\x91\xd1\x5d\xfe\x7b\xf6\xac\x92\xd4\xbd\x91\x2c\xa3",
                "LEO",
                18,
                "LEO Token",
            )
            yield (  # address, symbol, decimals, name
                b"\x51\x49\x10\x77\x1a\xf9\xca\x65\x6a\xf8\x40\xdf\xf8\x3e\x82\x64\xec\xf9\x86\xca",
                "LINK",
                18,
                "Chainlink",
            )
            yield (  # address, symbol, decimals, name
                b"\x0f\x5d\x2f\xb2\x9f\xb7\xd3\xcf\xee\x44\x4a\x20\x02\x98\xf4\x68\x90\x8c\xc9\x42",
                "MANA",
                18,
                "Decentraland",
            )
            yield (  # address, symbol, decimals, name
                b"\x7d\x1a\xfa\x7b\x71\x8f\xb8\x93\xdb\x30\xa3\xab\xc0\xcf\xc6\x08\xaa\xcf\xeb\xb0",
                "MATIC",
                18,
                "Polygon",
            )
            yield (  # address, symbol, decimals, name
                b"\x75\x23\x1f\x58\xb4\x32\x40\xc9\x71\x8d\xd5\x8b\x49\x67\xc5\x11\x43\x42\xa8\x6c",
                "OKB",
                18,
                "OKB",
            )
            yield (  # address, symbol, decimals, name
                b"\x4a\x22\x0e\x60\x96\xb2\x5e\xad\xb8\x83\x58\xcb\x44\x06\x8a\x32\x48\x25\x46\x75",
                "QNT",
                18,
                "Quant",
            )
            yield (  # address, symbol, decimals, name
                b"\x38\x45\xba\xda\xde\x8e\x6d\xff\x04\x98\x20\x68\x0d\x1f\x14\xbd\x39\x03\xa5\xd0",
                "SAND",
                18,
                "The Sandbox",
            )
            yield (  # address, symbol, decimals, name
                b"\x95\xad\x61\xb0\xa1\x50\xd7\x92\x19\xdc\xf6\x4e\x1e\x6c\xc0\x1f\x0b\x64\xc4\xce",
                "SHIB",
                18,
                "Shiba Inu",
            )
            yield (  # address, symbol, decimals, name
                b"\xae\x7a\xb9\x65\x20\xde\x3a\x18\xe5\xe1\x11\xb5\xea\xab\x09\x53\x12\xd7\xfe\x84",
                "STETH",
                18,
                "Lido Staked Ether",
            )
            yield (  # address, symbol, decimals, name
                b"\x1f\x98\x40\xa8\x5d\x5a\xf5\xbf\x1d\x17\x62\xf9\x25\xbd\xad\xdc\x42\x01\xf9\x84",
                "UNI",
                18,
                "Uniswap",
            )
            yield (  # address, symbol, decimals, name
                b"\xa0\xb8\x69\x91\xc6\x21\x8b\x36\xc1\xd1\x9d\x4a\x2e\x9e\xb0\xce\x36\x06\xeb\x48",
                "USDC",
                6,
                "USD Coin",
            )
            yield (  # address, symbol, decimals, name
                b"\xda\xc1\x7f\x95\x8d\x2e\xe5\x23\xa2\x20\x62\x06\x99\x45\x97\xc1\x3d\x83\x1e\xc7",
                "USDT",
                6,
                "Tether",
            )
            yield (  # address, symbol, decimals, name
                b"\x22\x60\xfa\xc5\xe5\x54\x2a\x77\x3a\xa4\x4f\xbc\xfe\xdf\x7c\x19\x3b\xc2\xc5\x99",
                "WBTC",
                8,
                "Wrapped Bitcoin",
            )
            yield (  # address, symbol, decimals, name
                b"\xa2\xcd\x3d\x43\xc7\x75\x97\x8a\x96\xbd\xbf\x12\xd7\x33\xd5\xa1\xed\x94\xfb\x18",
                "XCN",
                18,
                "Chain",
            )
        if chain_id == 56:  # bnb
            yield (  # address, symbol, decimals, name
                b"\x0e\xb3\xa7\x05\xfc\x54\x72\x50\x37\xcc\x9e\x00\x8b\xde\xde\x69\x7f\x62\xf3\x35",
                "ATOM",
                18,
                "Cosmos Hub",
            )
        if chain_id == 137:  # matic
            yield (  # address, symbol, decimals, name
                b"\x2c\x89\xbb\xc9\x2b\xd8\x6f\x80\x75\xd1\xde\xcc\x58\xc7\xf4\xe0\x10\x7f\x28\x6b",
                "WAVAX",
                18,
                "Wrapped AVAX",
            )
