from micropython import const
from ubinascii import unhexlify

# smart contract 'data' field lengths in bytes
SC_FUNC_SIG_BYTES = const(4)
SC_ARGUMENT_BYTES = const(32)
SC_ARGUMENT_ADDRESS_BYTES = const(20)
SC_FUNC_APPROVE_REVOKE_AMOUNT = const(0)

assert SC_ARGUMENT_ADDRESS_BYTES <= SC_ARGUMENT_BYTES

# Known ERC-20 functions

SC_FUNC_SIG_TRANSFER = unhexlify("a9059cbb")
SC_FUNC_SIG_APPROVE = unhexlify("095ea7b3")
SC_FUNC_SIG_STAKE = unhexlify("3a29dbae")
SC_FUNC_SIG_UNSTAKE = unhexlify("76ec871c")
SC_FUNC_SIG_CLAIM = unhexlify("33986ffa")

# EIP-7702

EIP_7702_TX_TYPE = const(4)
EIP_7702_KNOWN_ADDRESSES = {
    unhexlify("000000009B1D0aF20D8C6d0A44e162d11F9b8f00"): "Uniswap",
    unhexlify("69007702764179f14F51cdce752f4f775d74E139"): "alchemyplatform",
    unhexlify("5A7FC11397E9a8AD41BF10bf13F22B0a63f96f6d"): "AmbireTech",
    unhexlify("63c0c19a282a1b52b07dd5a65b58948a07dae32b"): "MetaMask",
    unhexlify(
        "4Cd241E8d1510e30b2076397afc7508Ae59C66c9"
    ): "Ethereum Foundation AA team",
    unhexlify("17c11FDdADac2b341F2455aFe988fec4c3ba26e3"): "Luganodes",
}


# Everstake staking

# addresses for pool (stake/unstake) and accounting (claim) operations
ADDRESSES_POOL = (
    unhexlify("AFA848357154a6a624686b348303EF9a13F63264"),  # Hoodi testnet
    unhexlify("D523794C879D9eC028960a231F866758e405bE34"),  # mainnet
)
ADDRESSES_ACCOUNTING = (
    unhexlify("624087DD1904ab122A32878Ce9e933C7071F53B9"),  # Hoodi testnet
    unhexlify("7a7f0b3c23C23a31cFcb0c44709be70d4D545c6e"),  # mainnet
)

# Approve known addresses
# This should eventually grow into a more comprehensive database and stored in some other way,
# but for now let's just keep a few known addresses here!

APPROVE_KNOWN_ADDRESSES = {
    unhexlify("e592427a0aece92de3edee1f18e0157c05861564"): "Uniswap V3 Router",
    unhexlify(
        "111111125421cA6dc452d289314280a0f8842A65"
    ): "1inch Aggregation Router V6",
    unhexlify("1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE"): "LiFI Diamond",
}
