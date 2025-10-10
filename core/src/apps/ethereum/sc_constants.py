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
